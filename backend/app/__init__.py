from flask import Flask, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

# 从 backend/.env 加载环境变量（该文件不提交到仓库）
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

INSECURE_SECRET_KEYS = {
    'change-me',
    'change-me-to-a-random-secret',
    'your-secret-key-change-in-production',
}


def _validated_secret_key(value):
    """拒绝缺失、占位或强度不足的 Flask 会话签名密钥。"""
    if not value or value in INSECURE_SECRET_KEYS or len(value.encode('utf-8')) < 32:
        raise RuntimeError(
            'SECRET_KEY must be set to a random value of at least 32 bytes'
        )
    return value


def _env_bool(name, default):
    """严格解析布尔环境变量，避免拼写错误静默降级。"""
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    raise RuntimeError(f'{name} must be true or false')


DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_NAME = os.environ.get('DB_NAME', 'photos_of_the_year')
raw_base_path = os.environ.get('APP_BASE_PATH', '').strip('/')
APP_BASE_PATH = f'/{raw_base_path}' if raw_base_path else ''

app = Flask(__name__)
app.config['SECRET_KEY'] = _validated_secret_key(os.environ.get('SECRET_KEY'))
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f'mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}/{DB_NAME}?charset=utf8mb4'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
app.config['APP_BASE_PATH'] = APP_BASE_PATH
app.config['PHOTO_CACHE_MAX_AGE'] = int(os.environ.get('PHOTO_CACHE_MAX_AGE', 2592000))
app.config['SESSION_COOKIE_SECURE'] = _env_bool('SESSION_COOKIE_SECURE', True)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'photos_of_the_year_session'
app.config['SESSION_COOKIE_PATH'] = f'{APP_BASE_PATH}/' if APP_BASE_PATH else '/'

# Serve static files from dist
app.static_folder = 'static/dist'
app.static_url_path = '/static'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.unauthorized_handler
def unauthorized():
    # 前后端分离：未登录统一返回 401 JSON，而非重定向到登录页
    return jsonify({'success': False, 'message': '未登录或登录已过期'}), 401

from app import routes, models
