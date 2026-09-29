#!/usr/bin/env python3
"""
Initialize the database and create the default users
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))

from app import app, db, bcrypt
from app.models import User

PLACEHOLDER_VALUES = {'change-me', 'your-password', 'your-mysql-password'}
MIN_PASSWORD_LENGTH = 8


def _required_env(name):
    value = os.environ.get(name, '').strip()
    if not value or value in PLACEHOLDER_VALUES:
        raise RuntimeError(f'{name} must be set to a non-placeholder value')
    return value


def _required_password(name):
    value = _required_env(name)
    if len(value) < MIN_PASSWORD_LENGTH:
        raise RuntimeError(
            f'{name} must contain at least {MIN_PASSWORD_LENGTH} characters'
        )
    return value


def main():
    # 默认账户凭据从 backend/.env 读取（app 初始化时已 load_dotenv）
    admin_username = _required_env('ADMIN_USERNAME')
    admin_password = _required_password('ADMIN_PASSWORD')
    user_username = _required_env('USER_USERNAME')
    user_password = _required_password('USER_PASSWORD')

    with app.app_context():
        db.create_all()
        print("Tables created")

        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            hashed_password = bcrypt.generate_password_hash(
                admin_password
            ).decode('utf-8')
            admin = User(
                username=admin_username,
                password_hash=hashed_password,
                is_admin=True
            )
            db.session.add(admin)
            print(f"Admin user '{admin_username}' created")
        else:
            print(f"Admin user '{admin_username}' already exists")

        user = User.query.filter_by(username=user_username).first()
        if not user:
            hashed_password = bcrypt.generate_password_hash(
                user_password
            ).decode('utf-8')
            user = User(
                username=user_username,
                password_hash=hashed_password,
                is_admin=False
            )
            db.session.add(user)
            print(f"Regular user '{user_username}' created")
        else:
            print(f"Regular user '{user_username}' already exists")

        db.session.commit()
        print("\nDatabase initialization complete!")


if __name__ == '__main__':
    main()
