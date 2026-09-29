"""
routes.py 的 API 单元测试.

覆盖: 认证、photos CRUD、users CRUD、权限校验、静态图片下载.
运行: cd backend && ../.venv-mac/bin/python -m pytest tests/ -v
"""
import os

import pytest

from app import db
from app.models import Photo, User

from conftest import make_upload


# ------------------------------------------------------------------
# 认证
# ------------------------------------------------------------------
class TestAuth:
    def test_login_成功返回用户信息(self, client, seed_users):
        resp = client.post(
            "/api/login",
            json={"username": "admin", "password": "admin_pw"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["user"]["username"] == "admin"
        assert data["user"]["is_admin"] is True

    def test_login_生产Cookie包含安全属性(
        self, client, seed_users, app, monkeypatch
    ):
        monkeypatch.setitem(app.config, "SESSION_COOKIE_SECURE", True)
        monkeypatch.setitem(
            app.config, "SESSION_COOKIE_PATH", "/photos-of-the-year/"
        )

        resp = client.post(
            "/api/login",
            json={"username": "admin", "password": "admin_pw"},
        )

        cookie = resp.headers["Set-Cookie"]
        assert cookie.startswith("photos_of_the_year_session=")
        assert "Secure" in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=Lax" in cookie
        assert "Path=/photos-of-the-year/" in cookie

    def test_login_密码错误返回401(self, client, seed_users):
        resp = client.post(
            "/api/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["success"] is False

    def test_login_用户不存在返回401(self, client, seed_users):
        resp = client.post(
            "/api/login",
            json={"username": "ghost", "password": "x"},
        )
        assert resp.status_code == 401

    def test_check_auth_未登录返回authenticated_false(self, client):
        resp = client.get("/api/check-auth")
        assert resp.status_code == 200
        assert resp.get_json() == {"authenticated": False}

    def test_check_auth_已登录返回用户信息(self, client, login_admin):
        resp = client.get("/api/check-auth")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["authenticated"] is True
        assert data["user"]["username"] == "admin"

    def test_logout_清除会话(self, client, login_admin):
        resp = client.post("/api/logout")
        assert resp.status_code == 200
        # 登出后 check-auth 应该未认证
        follow = client.get("/api/check-auth").get_json()
        assert follow["authenticated"] is False


# ------------------------------------------------------------------
# Photos GET
# ------------------------------------------------------------------
class TestGetPhotos:
    def test_未登录返回登录跳转(self, client):
        resp = client.get("/api/photos")
        # flask-login 未配置 login view 时返回 401 或 302
        assert resp.status_code in (401, 302)

    def test_返回全量照片按拍摄日期倒序(
        self, client, login_regular, sample_photos
    ):
        resp = client.get("/api/photos")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 4
        # shoot_date desc
        dates = [p["shoot_date"] for p in data]
        assert dates == sorted(dates, reverse=True)

    def test_按单年份过滤(self, client, login_regular, sample_photos):
        resp = client.get("/api/photos?year=2005")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        assert all(p["year"] == 2005 for p in data)

    def test_多年份过滤(self, client, login_regular, sample_photos):
        resp = client.get("/api/photos?year=2005&year=2026")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 4

    def test_空year参数被忽略(self, client, login_regular, sample_photos):
        resp = client.get("/api/photos?year=")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 4

    def test_image_url拼接正确(
        self, client, login_regular, sample_photos
    ):
        resp = client.get("/api/photos?year=2026")
        for p in resp.get_json():
            assert p["image_url"] == f"/uploads/{p['year']}/{p['filename']}"


class TestGetSinglePhoto:
    def test_获取存在的照片(self, client, login_regular, sample_photos):
        pid = sample_photos[0]
        resp = client.get(f"/api/photos/{pid}")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == pid

    def test_不存在时404(self, client, login_regular):
        resp = client.get("/api/photos/9999")
        assert resp.status_code == 404


# ------------------------------------------------------------------
# Photos CREATE
# ------------------------------------------------------------------
class TestCreatePhoto:
    def _post(self, client, **overrides):
        form = {
            "year": "2026",
            "title": "hello",
            "description": "desc",
            "shoot_date": "2026-03-30",
            "file": make_upload(),
        }
        form.update(overrides)
        return client.post(
            "/api/photos", data=form, content_type="multipart/form-data"
        )

    def test_普通用户上传成功并记录归属(self, client, login_regular):
        resp = self._post(client)
        assert resp.status_code == 200
        assert resp.get_json()["photo"]["uploader_id"] == login_regular["id"]

    def test_admin上传成功并落库(self, client, login_admin, app):
        resp = self._post(client)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        photo = data["photo"]
        assert photo["year"] == 2026
        assert photo["title"] == "hello"

        with app.app_context():
            assert Photo.query.count() == 1
            row = Photo.query.first()
            # 文件名带时间戳前缀
            assert row.filename.endswith("_test.jpg")
            # 文件真实落到 UPLOAD_FOLDER/<year>/
            path = os.path.join(
                app.config["UPLOAD_FOLDER"], "2026", row.filename
            )
            assert os.path.isfile(path)

    def test_没有file字段返回400(self, client, login_admin):
        resp = client.post(
            "/api/photos",
            data={"year": "2026", "shoot_date": "2026-01-01"},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "没有上传文件" in resp.get_json()["message"]

    def test_文件名为空返回400(self, client, login_admin):
        resp = self._post(client, file=make_upload(name=""))
        assert resp.status_code == 400
        assert "未选择文件" in resp.get_json()["message"]

    def test_不支持的扩展名返回400(self, client, login_admin):
        resp = self._post(client, file=make_upload(name="malware.exe"))
        assert resp.status_code == 400
        assert "不支持的文件类型" in resp.get_json()["message"]

    def test_同年满10张后禁止再上传(
        self, client, login_admin, app
    ):
        from datetime import date

        with app.app_context():
            for i in range(10):
                db.session.add(
                    Photo(
                        year=2026,
                        title=f"t{i}",
                        shoot_date=date(2026, 1, 1),
                        filename=f"f{i}.jpg",
                        uploader_id=login_admin["id"],
                    )
                )
            db.session.commit()

        resp = self._post(client)
        assert resp.status_code == 400
        assert "10 张" in resp.get_json()["message"] or "10张" in resp.get_json()["message"]


# ------------------------------------------------------------------
# Photos UPDATE / DELETE
# ------------------------------------------------------------------
class TestUpdatePhoto:
    def test_admin修改成功(
        self, client, login_admin, sample_photos
    ):
        pid = sample_photos[0]
        resp = client.put(
            f"/api/photos/{pid}",
            json={
                "title": "new-title",
                "description": "new-desc",
                "shoot_date": "2026-06-01",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()["photo"]
        assert data["title"] == "new-title"
        assert data["description"] == "new-desc"
        assert data["shoot_date"] == "2026-06-01"

    def test_普通用户403(
        self, client, login_regular, sample_photos
    ):
        pid = sample_photos[0]
        resp = client.put(f"/api/photos/{pid}", json={"title": "x"})
        assert resp.status_code == 403

    def test_不存在的id_404(self, client, login_admin):
        resp = client.put("/api/photos/9999", json={"title": "x"})
        assert resp.status_code == 404

    def test_不带shoot_date时保留原日期(
        self, client, login_admin, sample_photos, app
    ):
        pid = sample_photos[0]
        with app.app_context():
            original = Photo.query.get(pid).shoot_date

        resp = client.put(
            f"/api/photos/{pid}", json={"title": "only-title"}
        )
        assert resp.status_code == 200

        with app.app_context():
            assert Photo.query.get(pid).shoot_date == original


class TestDeletePhoto:
    def test_admin删除照片同时删除文件(
        self, client, login_admin, app
    ):
        # 先创建一张真实带文件的照片
        year_dir = os.path.join(app.config["UPLOAD_FOLDER"], "2026")
        os.makedirs(year_dir, exist_ok=True)
        fpath = os.path.join(year_dir, "to_delete.jpg")
        with open(fpath, "wb") as f:
            f.write(b"data")

        with app.app_context():
            from datetime import date

            photo = Photo(
                year=2026,
                title="t",
                shoot_date=date(2026, 1, 1),
                filename="to_delete.jpg",
            )
            db.session.add(photo)
            db.session.commit()
            pid = photo.id

        resp = client.delete(f"/api/photos/{pid}")
        assert resp.status_code == 200
        assert not os.path.exists(fpath)
        with app.app_context():
            assert Photo.query.get(pid) is None

    def test_普通用户403(
        self, client, login_regular, sample_photos
    ):
        resp = client.delete(f"/api/photos/{sample_photos[0]}")
        assert resp.status_code == 403

    def test_不存在的id_404(self, client, login_admin):
        resp = client.delete("/api/photos/9999")
        assert resp.status_code == 404

    def test_磁盘无文件时也能删除记录(
        self, client, login_admin, sample_photos, app
    ):
        # sample_photos 只在 DB 有记录, 磁盘无实际文件
        pid = sample_photos[0]
        resp = client.delete(f"/api/photos/{pid}")
        assert resp.status_code == 200
        with app.app_context():
            assert Photo.query.get(pid) is None


# ------------------------------------------------------------------
# Years
# ------------------------------------------------------------------
class TestYears:
    def test_返回去重年份列表_倒序(
        self, client, login_regular, sample_photos
    ):
        resp = client.get("/api/years")
        assert resp.status_code == 200
        assert resp.get_json() == [2026, 2005]

    def test_无照片时返回空列表(self, client, login_regular):
        resp = client.get("/api/years")
        assert resp.status_code == 200
        assert resp.get_json() == []


# ------------------------------------------------------------------
# Users
# ------------------------------------------------------------------
class TestGetUsers:
    def test_admin拿到用户列表(
        self, client, login_admin, seed_users
    ):
        resp = client.get("/api/users")
        assert resp.status_code == 200
        data = resp.get_json()
        usernames = {u["username"] for u in data}
        assert usernames == {"admin", "alice"}

    def test_普通用户403(self, client, login_regular):
        resp = client.get("/api/users")
        assert resp.status_code == 403


class TestCreateUser:
    def test_admin创建成功(self, client, login_admin, app):
        resp = client.post(
            "/api/users",
            json={"username": "bob", "password": "pw", "is_admin": False},
        )
        assert resp.status_code == 200
        with app.app_context():
            assert User.query.filter_by(username="bob").first() is not None

    def test_用户名重复返回400(self, client, login_admin):
        resp = client.post(
            "/api/users",
            json={"username": "admin", "password": "pw"},
        )
        assert resp.status_code == 400
        assert "已存在" in resp.get_json()["message"]

    def test_普通用户403(self, client, login_regular):
        resp = client.post(
            "/api/users", json={"username": "x", "password": "y"}
        )
        assert resp.status_code == 403


class TestUpdateUser:
    def test_admin修改用户名(
        self, client, login_admin, seed_users, app
    ):
        uid = seed_users["regular"]["id"]
        resp = client.put(
            f"/api/users/{uid}",
            json={"username": "alice2", "is_admin": False},
        )
        assert resp.status_code == 200
        with app.app_context():
            assert User.query.get(uid).username == "alice2"

    def test_修改时用户名冲突返回400(
        self, client, login_admin, seed_users
    ):
        uid = seed_users["regular"]["id"]
        resp = client.put(
            f"/api/users/{uid}", json={"username": "admin"}
        )
        assert resp.status_code == 400

    def test_可选修改密码(
        self, client, login_admin, seed_users, app
    ):
        uid = seed_users["regular"]["id"]
        resp = client.put(
            f"/api/users/{uid}",
            json={
                "username": "alice",
                "is_admin": False,
                "password": "new_pw",
            },
        )
        assert resp.status_code == 200

        # 用新密码登录应成功
        client.post("/api/logout")
        login_resp = client.post(
            "/api/login",
            json={"username": "alice", "password": "new_pw"},
        )
        assert login_resp.status_code == 200

    def test_普通用户403(self, client, login_regular, seed_users):
        uid = seed_users["regular"]["id"]
        resp = client.put(f"/api/users/{uid}", json={"username": "x"})
        assert resp.status_code == 403


class TestDeleteUser:
    def test_admin删除其他用户(
        self, client, login_admin, seed_users, app
    ):
        uid = seed_users["regular"]["id"]
        resp = client.delete(f"/api/users/{uid}")
        assert resp.status_code == 200
        with app.app_context():
            assert User.query.get(uid) is None

    def test_不能删除自己(
        self, client, login_admin, seed_users
    ):
        uid = seed_users["admin"]["id"]
        resp = client.delete(f"/api/users/{uid}")
        assert resp.status_code == 400
        assert "当前登录" in resp.get_json()["message"]

    def test_普通用户403(self, client, login_regular, seed_users):
        uid = seed_users["regular"]["id"]
        resp = client.delete(f"/api/users/{uid}")
        assert resp.status_code == 403


# ------------------------------------------------------------------
# 静态图片下载
# ------------------------------------------------------------------
class TestUploadedFile:
    def test_未登录不能访问原图和缩略图(self, client):
        assert client.get("/uploads/2026/photo.jpg").status_code == 401
        assert client.get("/uploads/2026/thumbs/photo.jpg").status_code == 401

    def test_登录后下载已存在的照片(
        self, client, login_regular, app, monkeypatch
    ):
        monkeypatch.setitem(app.config, "PHOTO_CACHE_MAX_AGE", 60)
        year_dir = os.path.join(app.config["UPLOAD_FOLDER"], "2026")
        os.makedirs(year_dir, exist_ok=True)
        fpath = os.path.join(year_dir, "photo.jpg")
        with open(fpath, "wb") as f:
            f.write(b"binary-data")

        resp = client.get("/uploads/2026/photo.jpg")
        assert resp.status_code == 200
        assert resp.data == b"binary-data"
        assert "private" in resp.headers["Cache-Control"]
        assert "max-age=60" in resp.headers["Cache-Control"]
        assert "immutable" in resp.headers["Cache-Control"]
        assert "Cookie" in resp.headers["Vary"]

    def test_登录后下载缩略图(self, client, login_regular, app):
        thumb_dir = os.path.join(
            app.config["UPLOAD_FOLDER"], "2026", "thumbs"
        )
        os.makedirs(thumb_dir, exist_ok=True)
        fpath = os.path.join(thumb_dir, "photo.jpg")
        with open(fpath, "wb") as f:
            f.write(b"thumbnail-data")

        resp = client.get("/uploads/2026/thumbs/photo.jpg")
        assert resp.status_code == 200
        assert resp.data == b"thumbnail-data"
        assert "private" in resp.headers["Cache-Control"]
        assert "max-age=2592000" in resp.headers["Cache-Control"]
        assert "immutable" in resp.headers["Cache-Control"]

    def test_登录后访问不存在文件返回404(self, client, login_regular):
        resp = client.get("/uploads/2026/none.jpg")
        assert resp.status_code == 404
