"""
共享 fixture: 用 SQLite 内存库替换 MySQL, 隔离每个测试的数据库和上传目录.

app 在 import 时就绑定了 MySQL URI, 所以这里必须在 import 后立即
覆盖 config 并重新绑定 SQLAlchemy engine.

安全防护: 每次执行 create_all/drop_all 前都会 assert engine 是 sqlite,
防止误操作把开发者本地 MySQL 里的业务数据清掉.
"""
import io
import os
import sys

import pytest

# 让测试可以直接 import backend.app
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# 关键: 在 import app 之前就把 URI 换成一个绝对不可能连上真实 MySQL 的值.
# app/__init__.py 里的 URI 是模块级 config 赋值, 这里的环境变量兜底不影响,
# 因此还需要 _configured_app fixture 里显式 rebind engine.
os.environ.setdefault("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-at-least-32-bytes")
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")

from app import app as flask_app  # noqa: E402
from app import bcrypt, db  # noqa: E402
from app.models import Photo, User  # noqa: E402


def _assert_sqlite_engine():
    """防呆: 保证当前 default engine 指向 sqlite 而非 MySQL/PG."""
    url = str(db.engine.url)
    assert url.startswith("sqlite:"), (
        f"UNSAFE: current engine is {url!r}. "
        "Refusing to run destructive DDL (drop_all/create_all). "
        "This usually means _configured_app fixture failed to rebind engine."
    )


@pytest.fixture(scope="session")
def _configured_app(tmp_path_factory):
    """Session 级: 只初始化一次 engine, 避免 Flask 'setup after request' 报错.

    实现要点: flask-sqlalchemy 3.x 只在 init_app 时读一次 URI 建 engine,
    之后 config 的变化不会生效. 这里绕过 __init__.py 里已注册的 MySQL engine,
    用 sqlite 覆盖后重新 init_app.
    """
    tmp_root = tmp_path_factory.mktemp("photos_test")
    upload_dir = tmp_root / "uploads"
    upload_dir.mkdir()
    db_path = tmp_root / "test.db"

    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        UPLOAD_FOLDER=str(upload_dir),
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test-secret",
        SESSION_COOKIE_SECURE=False,
    )

    # 清扩展和 engine 缓存, 触发一次 init_app 使新 URI 生效.
    flask_app.extensions.pop("sqlalchemy", None)
    if hasattr(db, "_app_engines"):
        old_engines = db._app_engines.pop(flask_app, {})
        for eng in old_engines.values():
            eng.dispose()
    db.init_app(flask_app)

    # 立刻验证 rebind 成功, 而不是等到第一个测试的 drop_all 时才发现.
    with flask_app.app_context():
        _assert_sqlite_engine()

    return flask_app, upload_dir


@pytest.fixture
def app(_configured_app):
    """每个测试拿到干净的 sqlite 表."""
    flask_app_obj, _upload_dir = _configured_app

    with flask_app_obj.app_context():
        _assert_sqlite_engine()  # 每次都验一遍, 双保险
        db.drop_all()
        db.create_all()
        try:
            yield flask_app_obj
        finally:
            db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_users(app):
    """创建 admin 和 regular 用户, 返回 dict."""
    with app.app_context():
        admin = User(
            username="admin",
            password_hash=bcrypt.generate_password_hash("admin_pw").decode("utf-8"),
            is_admin=True,
        )
        regular = User(
            username="alice",
            password_hash=bcrypt.generate_password_hash("alice_pw").decode("utf-8"),
            is_admin=False,
        )
        db.session.add_all([admin, regular])
        db.session.commit()
        return {
            "admin": {"id": admin.id, "username": "admin", "password": "admin_pw"},
            "regular": {"id": regular.id, "username": "alice", "password": "alice_pw"},
        }


@pytest.fixture
def login_admin(client, seed_users):
    resp = client.post(
        "/api/login",
        json={"username": "admin", "password": "admin_pw"},
    )
    assert resp.status_code == 200
    return seed_users["admin"]


@pytest.fixture
def login_regular(client, seed_users):
    resp = client.post(
        "/api/login",
        json={"username": "alice", "password": "alice_pw"},
    )
    assert resp.status_code == 200
    return seed_users["regular"]


@pytest.fixture
def sample_photos(app):
    """插入 4 张测试照片, 覆盖两个年份."""
    from datetime import date

    with app.app_context():
        photos = [
            Photo(year=2026, title="A", description="d1",
                  shoot_date=date(2026, 3, 30), filename="a.jpg"),
            Photo(year=2026, title="B", description="d2",
                  shoot_date=date(2026, 3, 18), filename="b.jpg"),
            Photo(year=2005, title="C", description=None,
                  shoot_date=date(2005, 9, 1), filename="c.jpg"),
            Photo(year=2005, title=None, description="d4",
                  shoot_date=date(2005, 11, 11), filename="d.jpg"),
        ]
        db.session.add_all(photos)
        db.session.commit()
        return [p.id for p in photos]


def make_upload(name="test.jpg", content=b"\xff\xd8\xff\xe0fake-jpeg-bytes"):
    """构造 (BytesIO, filename) 元组供 test_client post 用."""
    return (io.BytesIO(content), name)
