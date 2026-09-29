import os
from functools import wraps
from datetime import datetime
from flask import request, jsonify, send_from_directory, current_app
from flask_login import login_user, current_user, logout_user, login_required
from app import app, db, bcrypt
from app.models import User, Photo
from werkzeug.utils import secure_filename
from PIL import Image

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
THUMBNAIL_SIZE = (600, 600)  # 缩略图最大边长，保持宽高比

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    """要求当前用户已登录且为管理员，否则返回 403。"""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403
        return f(*args, **kwargs)
    return decorated

def _can_manage(photo):
    """管理员可管理任意照片；普通用户仅能管理自己上传的照片。"""
    return current_user.is_admin or photo.uploader_id == current_user.id

def _thumb_path(year, filename):
    return os.path.join(current_app.config['UPLOAD_FOLDER'], str(year), 'thumbs', filename)

def _generate_thumbnail(src_path, year, filename):
    """为原图生成缩略图，失败不阻断主流程。"""
    thumb_path = _thumb_path(year, filename)
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    try:
        with Image.open(src_path) as img:
            img.thumbnail(THUMBNAIL_SIZE)
            img.save(thumb_path)
        return True
    except Exception as e:
        current_app.logger.warning(f'生成缩略图失败 {filename}: {e}')
        return False

def _send_private_file(directory, filename):
    """发送仅限已登录用户访问的文件，并允许浏览器私有缓存。"""
    response = send_from_directory(directory, filename)
    max_age = current_app.config['PHOTO_CACHE_MAX_AGE']
    response.headers['Cache-Control'] = f'private, max-age={max_age}, immutable'
    response.vary.add('Cookie')
    return response

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'is_admin': user.is_admin
            }
        })
    return jsonify({'success': False, 'message': '登录失败，请检查用户名和密码'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    logout_user()
    return jsonify({'success': True, 'message': '已退出登录'})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'is_admin': current_user.is_admin
            }
        })
    return jsonify({'authenticated': False})

@app.route('/api/photos', methods=['GET'])
@login_required
def get_photos():
    # Flask request.args.getlist('year') correctly gets multiple values with same name
    years = request.args.getlist('year')
    # Filter out empty values
    years = [y for y in years if y]
    query = Photo.query
    if years:
        # 转换为整数并过滤，忽略非法值
        try:
            year_list = [int(y) for y in years]
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '年份参数无效'}), 400
        query = query.filter(Photo.year.in_(year_list))

    # 上传者筛选（多值），不传则返回全部
    uploaders = [u for u in request.args.getlist('uploader') if u]
    if uploaders:
        try:
            uploader_list = [int(u) for u in uploaders]
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '上传者参数无效'}), 400
        query = query.filter(Photo.uploader_id.in_(uploader_list))

    photos = query.order_by(Photo.shoot_date.desc()).all()
    return jsonify([photo.to_dict() for photo in photos])

@app.route('/api/photos/<int:photo_id>', methods=['GET'])
@login_required
def get_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    return jsonify(photo.to_dict())

@app.route('/api/photos', methods=['POST'])
@login_required
def create_photo():
    # 校验并解析年份（拍摄日期驱动，非法输入返回 400 而非 500）
    try:
        year = int(request.form.get('year'))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': '年份无效'}), 400
    title = request.form.get('title')
    description = request.form.get('description')
    shoot_date_str = request.form.get('shoot_date')

    # 校验拍摄日期
    try:
        shoot_date = datetime.strptime(shoot_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': '拍摄日期无效'}), 400

    # 每个用户每个年份最多10张（各自独立计数）
    count = Photo.query.filter_by(year=year, uploader_id=current_user.id).count()
    if count >= 10:
        return jsonify({'success': False, 'message': '你在该年份已达到最多10张照片的限制'}), 400

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # 添加时间戳避免重名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{filename}"

        # 按年份创建目录
        year_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(year))
        os.makedirs(year_dir, exist_ok=True)

        file_path = os.path.join(year_dir, filename)
        file.save(file_path)

        # 生成缩略图（失败不阻断上传）
        _generate_thumbnail(file_path, year, filename)

        photo = Photo(
            year=year,
            title=title,
            description=description,
            shoot_date=shoot_date,
            filename=filename,
            uploader_id=current_user.id
        )
        db.session.add(photo)
        db.session.commit()

        return jsonify({'success': True, 'photo': photo.to_dict()})

    return jsonify({'success': False, 'message': '不支持的文件类型'}), 400

@app.route('/api/photos/<int:photo_id>', methods=['PUT'])
@login_required
def update_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if not _can_manage(photo):
        return jsonify({'success': False, 'message': '只能管理自己上传的照片'}), 403
    data = request.get_json()

    photo.title = data.get('title')
    photo.description = data.get('description')
    if data.get('shoot_date'):
        try:
            photo.shoot_date = datetime.strptime(data.get('shoot_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '拍摄日期无效'}), 400

    db.session.commit()

    return jsonify({'success': True, 'photo': photo.to_dict()})

@app.route('/api/photos/<int:photo_id>', methods=['DELETE'])
@login_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if not _can_manage(photo):
        return jsonify({'success': False, 'message': '只能管理自己上传的照片'}), 403

    # 删除原图
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], str(photo.year), photo.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    # 删除缩略图
    thumb_path = _thumb_path(photo.year, photo.filename)
    if os.path.exists(thumb_path):
        os.remove(thumb_path)

    db.session.delete(photo)
    db.session.commit()

    return jsonify({'success': True, 'message': '删除成功'})

@app.route('/api/years', methods=['GET'])
@login_required
def get_years():
    years = db.session.query(Photo.year).distinct().order_by(Photo.year.desc()).all()
    years_list = [year[0] for year in years]
    return jsonify(years_list)

@app.route('/api/uploaders', methods=['GET'])
@login_required
def get_uploaders():
    # 返回有照片的上传者列表（去重），供筛选下拉使用
    rows = (
        db.session.query(User.id, User.username)
        .join(Photo, Photo.uploader_id == User.id)
        .distinct()
        .order_by(User.username)
        .all()
    )
    return jsonify([{'id': uid, 'username': uname} for uid, uname in rows])

@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    users = User.query.all()
    result = []
    for user in users:
        result.append({
            'id': user.id,
            'username': user.username,
            'is_admin': user.is_admin
        })
    return jsonify(result)

@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(username=username, password_hash=hashed_password, is_admin=is_admin)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'is_admin': user.is_admin
        }
    })

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    # 检查用户名是否被其他用户使用
    existing = User.query.filter_by(username=data.get('username')).first()
    if existing and existing.id != user_id:
        return jsonify({'success': False, 'message': '用户名已被使用'}), 400

    user.username = data.get('username')
    user.is_admin = data.get('is_admin', False)

    # 如果提供了新密码，更新密码
    if data.get('password'):
        user.password_hash = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')

    db.session.commit()

    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'is_admin': user.is_admin
        }
    })

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': '不能删除当前登录的用户'}), 400

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()

    return jsonify({'success': True, 'message': '删除成功'})

@app.route('/uploads/<year>/<filename>')
@login_required
def uploaded_file(year, filename):
    year_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], year)
    return _send_private_file(year_dir, filename)

@app.route('/uploads/<year>/thumbs/<filename>')
@login_required
def thumbnail_file(year, filename):
    """返回缩略图；若缩略图不存在则惰性生成，仍失败则回退原图。"""
    thumb_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], year, 'thumbs')
    thumb_full = os.path.join(thumb_dir, filename)
    if not os.path.exists(thumb_full):
        src_path = os.path.join(current_app.config['UPLOAD_FOLDER'], year, filename)
        if os.path.exists(src_path):
            _generate_thumbnail(src_path, year, filename)
    if os.path.exists(thumb_full):
        return _send_private_file(thumb_dir, filename)
    # 回退到原图
    return _send_private_file(
        os.path.join(current_app.config['UPLOAD_FOLDER'], year),
        filename
    )

# Serve assets from dist/assets
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(app.static_folder, 'assets'), filename)

# Catch-all route for SPA
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return send_from_directory(app.static_folder, 'index.html')
