from app import db, login_manager
from flask import current_app
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"User('{self.username}', '{'Admin' if self.is_admin else 'User'}')"

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(200), nullable=True)
    shoot_date = db.Column(db.Date, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploader = db.relationship('User', backref='photos')

    def to_dict(self):
        """序列化为 API 返回的字典，统一各路由的照片输出格式。"""
        base_path = current_app.config.get('APP_BASE_PATH', '')
        return {
            'id': self.id,
            'year': self.year,
            'title': self.title,
            'description': self.description,
            'shoot_date': self.shoot_date.strftime('%Y-%m-%d'),
            'filename': self.filename,
            'image_url': f'{base_path}/uploads/{self.year}/{self.filename}',
            'thumbnail_url': f'{base_path}/uploads/{self.year}/thumbs/{self.filename}',
            'uploader_id': self.uploader_id,
            'uploader': self.uploader.username if self.uploader else None,
        }

    def __repr__(self):
        return f"Photo({self.year}, '{self.title}', {self.shoot_date})"
