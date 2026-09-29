# Photos of the Year

一个照片管理网站，管理年度照片，支持按多用户、年份管理照片。

## 技术栈

- **前端**: Vue 3 (Vite)
- **后端**: Flask
- **数据库**: MySQL
- **Web服务器**: Nginx + Gunicorn

## 功能特性

- 🔐 需要登录认证才能访问
- 👥 两种用户类型：管理员和普通用户
- 📸 每位用户可以按年份上传照片（每人每年最多10张）
- ✏️ 普通用户只能修改、删除自己上传的照片，管理员可以管理全部照片
- 📅 每张照片需要填写拍摄日期，支持标题和备注
- 📷 选择照片后自动读取 EXIF 拍摄日期；无法读取时可手动选择，自动结果也可修改
- 📂 照片按年份目录存储
- 👤 管理员可以管理用户（新增、删除、修改）
- 🖼️ 普通用户可以浏览所有照片
- 🙋 记录每张照片的上传者，展示与管理页面均可按年份、上传者多选筛选（默认不选即全部）

## 默认账户

初始化脚本会创建一个管理员账户和一个普通用户账户，具体的用户名和密码在 `backend/.env` 中配置（见下方「环境变量配置」）。仓库中不包含真实凭据。

## 隐私照片与 Git 安全

`backend/uploads/` 保存用户上传的原图和缩略图，属于隐私数据：

- 原图和缩略图路由均由 Flask 执行登录鉴权，匿名请求返回 `401`。
- 当前权限模型允许所有已登录用户浏览全部照片；普通用户只能修改、删除本人上传的照片。
- Nginx 的 uploads 路径必须代理到 Flask，不能使用 `alias` 或其他静态目录映射绕过鉴权。
- 生产会话 Cookie 启用 `Secure`、`HttpOnly` 和 `SameSite=Lax`，Nginx 通过 HSTS 强制后续 HTTPS 访问。
- 照片响应使用浏览器私有缓存，不允许共享代理缓存；默认缓存30天，可通过 `PHOTO_CACHE_MAX_AGE` 调整。
- `.gitignore` 已忽略整个 `backend/uploads/`，不要使用 `git add -f` 强制提交该目录，也不要将照片上传到公开 Git 仓库。

如果照片曾被 Git 跟踪，仅修改 `.gitignore` 不会自动解除跟踪，需要执行：

```bash
git rm -r --cached backend/uploads/
git commit -m "stop tracking private uploads"
```

部署或备份时应通过受控的 SSH、SCP、rsync 等方式单独传输照片，并限制备份文件的访问权限。

## 部署说明

### 1. 环境要求

- Python 3.8+
- Node.js 18+
- MySQL 5.7+
- Nginx

### 2. 环境变量配置

敏感信息（数据库密码、默认账户、Flask 密钥）统一通过 `backend/.env` 配置，该文件已被 `.gitignore` 忽略，不会提交到仓库。

复制示例文件并填入真实值：

```bash
cd backend
cp .env.example .env
# 然后编辑 .env 填入真实的数据库密码、账户凭据等
```

`.env` 可配置项：

| 变量 | 说明 |
|------|------|
| `SECRET_KEY` | 必填；至少32字节的 Flask 会话签名密钥。可用 `python3 -c "import secrets; print(secrets.token_hex(32))"` 生成 |
| `SESSION_COOKIE_SECURE` | 生产 HTTPS 环境必须为 `true`；仅本地 HTTP 开发设为 `false` |
| `DB_USER` / `DB_PASSWORD` | MySQL 用户名 / 密码 |
| `DB_HOST` / `DB_NAME` | MySQL 主机 / 数据库名 |
| `APP_BASE_PATH` | 部署子路径；根路径部署时留空，例如 `/photos-of-the-year` |
| `PHOTO_CACHE_MAX_AGE` | 照片浏览器私有缓存时长（秒），默认 `2592000`（30天） |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 必填；初始化脚本创建的管理员账户，密码至少8位 |
| `USER_USERNAME` / `USER_PASSWORD` | 必填；初始化脚本创建的普通用户账户，密码至少8位 |

应用会拒绝缺失、过短或仍为示例占位值的密钥与初始化密码，不再使用公开默认凭据。

### 3. 数据库配置

确保 MySQL 已经运行，并且 `.env` 中的 `DB_USER` / `DB_PASSWORD` 与实际一致，允许 `127.0.0.1` 访问。然后创建数据库：

```bash
mysql -u "$DB_USER" -p -e "CREATE DATABASE IF NOT EXISTS photos_of_the_year CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 4. 依赖安装脚本

项目提供依赖安装、前端构建和数据库初始化脚本。根路径部署可直接运行；子路径部署需传入 `VITE_BASE_PATH`：

```bash
cd photos-of-the-year
VITE_BASE_PATH=/photos-of-the-year/ ./deploy/deploy.sh
```

脚本不修改 systemd 或现有 Nginx 站点，生产环境仍需完成下方配置。

### 5. 手动部署步骤

**安装后端依赖**

```bash
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

**配置环境变量**（参见上方「环境变量配置」）

```bash
cp .env.example .env
# 子路径部署时设置 APP_BASE_PATH=/photos-of-the-year
```

**安装前端依赖并构建**

```bash
cd ../frontend
npm install
VITE_BASE_PATH=/photos-of-the-year/ npm run build
```

根路径部署时直接运行 `npm run build`。

**初始化数据库和创建默认用户**

```bash
cd ../deploy
python init_db.py
```

**创建上传目录**

```bash
mkdir -p ../backend/uploads
```

### 6. 配置 Gunicorn

仓库中的 `deploy/photos-of-the-year.service` 对应以下生产路径和端口：

- 项目目录：`/usr/share/nginx/html/photos-of-the-year`
- Gunicorn：`127.0.0.1:5002`
- 运行用户：`nginx`
- 应用前缀：`/photos-of-the-year`

安装并启动：

```bash
sudo cp deploy/photos-of-the-year.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now photos-of-the-year
sudo systemctl status photos-of-the-year
```

### 7. 配置 Nginx

将子路径配置安装为 snippet：

```bash
sudo mkdir -p /etc/nginx/snippets
sudo cp deploy/nginx/photos-of-the-year.locations.conf \
  /etc/nginx/snippets/photos-of-the-year.conf
```

在域名现有 HTTPS `server` 块中加入（不要放入 HTTP `server` 块）：

```nginx
include /etc/nginx/snippets/photos-of-the-year.conf;
```

检查并重载，不需要替换现有站点配置：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 8. 当前生产部署

- 访问地址：<https://smilejay.cn/photos-of-the-year/>
- systemd 服务：`photos-of-the-year.service`
- 服务日志：`journalctl -u photos-of-the-year.service`
- Nginx 配置：`/etc/nginx/conf.d/smilejay.conf`
- Nginx snippet：`/etc/nginx/snippets/photos-of-the-year.conf`

重新发布前端时必须使用相同的构建前缀：

```bash
cd /usr/share/nginx/html/photos-of-the-year/frontend
VITE_BASE_PATH=/photos-of-the-year/ npm run build
sudo systemctl restart photos-of-the-year
```

## 项目结构

```
photos-of-the-year/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask app 初始化
│   │   ├── models.py            # 数据模型 (User, Photo)
│   │   ├── routes.py            # API 路由
│   │   └── static/
│   │       └── dist/            # 前端构建输出
│   ├── uploads/                 # 隐私照片，不提交 Git
│   ├── requirements.txt         # Python 依赖
│   ├── run.py                   # 开发运行
│   └── wsgi.py                  # WSGI 入口
├── frontend/
│   ├── src/
│   │   ├── main.js              # Vue 入口
│   │   ├── App.vue              # 根组件
│   │   ├── router/              # 路由配置
│   │   ├── stores/              # Pinia 状态管理 (auth)
│   │   ├── views/               # 页面组件
│   │   │   ├── Login.vue
│   │   │   ├── Gallery.vue
│   │   │   ├── Admin.vue
│   │   │   └── UserManagement.vue
│   │   └── style.css            # 全局样式
│   ├── vite.config.js           # Vite 配置
│   └── package.json
├── deploy/
│   ├── deploy.sh                # 依赖安装与构建脚本
│   ├── init_db.py               # 初始化数据库
│   ├── nginx/
│   │   └── photos-of-the-year.locations.conf
│   ├── restore_db.sh            # 从备份恢复数据库
│   └── photos-of-the-year.service
├── LICENSE
└── README.md
```

## 数据模型

数据库名称为 `photos_of_the_year`，数据表使用 InnoDB、`utf8mb4` 字符集和 `utf8mb4_unicode_ci` 排序规则。

| 表 | 说明 | 关键字段 |
|---|---|---|
| `user` | 登录用户与管理员账户 | `id`、`username`、`password_hash`、`is_admin` |
| `photo` | 年度照片及其上传信息 | `id`、`year`、`shoot_date`、`filename`、`uploader_id` |

关系：`user.id` 一对多关联 `photo.uploader_id`。删除用户时不会删除照片，数据库通过 `ON DELETE SET NULL` 将对应照片的 `uploader_id` 置空。

### `user` 表

| 字段 | MySQL 类型 | 可空 | 约束 / 默认值 | 说明 |
|---|---|---|---|---|
| `id` | `INT` | 否 | 主键、自增 | 用户 ID |
| `username` | `VARCHAR(20)` | 否 | 唯一索引 | 登录用户名 |
| `password_hash` | `VARCHAR(60)` | 否 | - | Bcrypt 密码哈希，不存储明文密码 |
| `is_admin` | `TINYINT(1)` | 是 | ORM 新建用户时默认为 `false` | 是否为管理员 |

### `photo` 表

| 字段 | MySQL 类型 | 可空 | 约束 / 默认值 | 说明 |
|---|---|---|---|---|
| `id` | `INT` | 否 | 主键、自增 | 照片记录 ID |
| `year` | `INT` | 否 | - | 照片所属年份 |
| `title` | `VARCHAR(100)` | 是 | `NULL` | 标题 |
| `description` | `VARCHAR(200)` | 是 | `NULL` | 备注 |
| `shoot_date` | `DATE` | 否 | - | 拍摄日期 |
| `filename` | `VARCHAR(255)` | 否 | - | uploads 目录中的文件名 |
| `created_at` | `DATETIME` | 是 | 由 SQLAlchemy 在新增时写入 UTC 时间 | 创建时间 |
| `updated_at` | `DATETIME` | 是 | 由 SQLAlchemy 在新增和更新时写入 UTC 时间 | 最后更新时间 |
| `uploader_id` | `INT` | 是 | 普通索引、外键 → `user.id` | 上传者；用户删除后置为 `NULL` |

## 存储结构

上传的照片按年份分目录存储，缩略图位于各年份的 `thumbs/` 子目录：

```
backend/uploads/
├── 2023/
│   ├── 20240330120000_photo1.jpg
│   └── 20240330120100_photo2.jpg
└── 2024/
    ├── 20240330120200_holiday.jpg
    └── ...
```

该目录包含隐私照片，已被 `.gitignore` 整体忽略，不应提交到 Git 仓库。线上访问必须经过上述 Flask 登录鉴权。

## API 端点

- `POST /api/login` - 用户登录
- `POST /api/logout` - 用户登出
- `GET /api/check-auth` - 检查认证状态
- `GET /api/photos` - 获取照片列表（支持 `?year=` 和 `?uploader=` 多值筛选，均可叠加，不传即全部）
- `POST /api/photos` - 创建新照片（所有登录用户；每人每年最多10张）
- `PUT /api/photos/:id` - 更新照片（本人或管理员）
- `DELETE /api/photos/:id` - 删除照片（本人或管理员）
- `GET /api/years` - 获取有照片的年份列表
- `GET /api/uploaders` - 获取有照片的上传者列表 (供筛选使用)
- `GET /api/users` - 获取用户列表 (管理员)
- `POST /api/users` - 创建用户 (管理员)
- `PUT /api/users/:id` - 更新用户 (管理员)
- `DELETE /api/users/:id` - 删除用户 (管理员)
- `GET /uploads/<year>/<filename>` - 获取上传的原图（需登录，默认私有缓存30天）
- `GET /uploads/<year>/thumbs/<filename>` - 获取缩略图（需登录，默认私有缓存30天；不存在时惰性生成）

## 开发模式

**后端开发**
```bash
cd backend
python run.py
# 运行在 http://127.0.0.1:5000
```

**前端开发**
```bash
cd frontend
npm run dev
# 运行在 http://127.0.0.1:3000，自动代理 API 请求到后端
```

## License

[MIT](LICENSE)
