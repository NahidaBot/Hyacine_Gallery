# Hyacine Gallery

多平台图片画廊应用，支持 Web 前端浏览、管理面板、多平台爬虫导入和 Telegram Bot 投稿。

## 技术栈

| 模块 | 技术 |
|------|------|
| 后端 | Python 3.14+, FastAPI, SQLAlchemy (async), Alembic, uv |
| 前端 | Next.js 16 (App Router), TypeScript, Tailwind CSS 4, React 19, pnpm |
| 数据库 | SQLite (开发) / PostgreSQL 16 (生产) |
| Bot | python-telegram-bot |
| 爬虫 | Pixiv API, fxtwitter API, gallery-dl (通用回退) |
| 部署 | Docker Compose |

## 项目结构

```
├── backend/               FastAPI 后端
│   ├── app/
│   │   ├── api/           路由 (artworks, tags, admin)
│   │   ├── crawlers/      爬虫 (pixiv, twitter, gallery-dl)
│   │   ├── models/        SQLAlchemy 模型
│   │   ├── schemas/       Pydantic 请求/响应模型
│   │   └── services/      业务逻辑层
│   └── alembic/           数据库迁移
├── frontend/              Next.js 前端
│   └── src/
│       ├── app/           页面 (gallery, artwork, tags, panel)
│       ├── components/    组件 (ArtworkCard, ArtworkGrid)
│       ├── lib/           API 客户端 (api.ts, admin-api.ts)
│       └── types/         TypeScript 类型定义
├── bots/telegram/         Telegram Bot 独立进程
│   ├── handlers/          命令处理器
│   ├── client.py          后端 API 客户端
│   └── config.py          配置
├── docker-compose.yml     生产环境
└── docker-compose.dev.yml 开发环境覆盖
```

## 快速开始

### 环境要求

- Python 3.14+, [uv](https://docs.astral.sh/uv/)
- Node.js 22+, [pnpm](https://pnpm.io/)
- (可选) Docker & Docker Compose

### 1. 复制环境变量

```bash
cp .env.example .env
# 编辑 .env，至少修改 ADMIN_PANEL_SLUG 和 ADMIN_TOKEN
```

### 2. 启动后端

```bash
cd backend
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
alembic upgrade head        # 初始化数据库
uvicorn app.main:app --reload  # 启动开发服务器 :8000
```

默认使用 SQLite（文件：`backend/hyacine_gallery.db`），无需额外配置。
生产环境在 `.env` 中设置 `DATABASE_URL=postgresql+asyncpg://...` 切换到 PostgreSQL。

### 3. 启动前端

```bash
cd frontend
pnpm install
pnpm dev                    # 启动开发服务器 :3000
```

### 4. 启动 Telegram Bot（可选）

```bash
cd bots/telegram
uv venv && source .venv/bin/activate
uv pip install -e "."
# 确保 .env 中配置了 TELEGRAM_BOT_TOKEN
python -m main
```

### 5. Docker（全栈）

```bash
docker compose up -d                                                 # 生产
docker compose -f docker-compose.yml -f docker-compose.dev.yml up    # 开发
```

## 功能说明

### Web 前端

| 页面 | 路径 | 说明 |
|------|------|------|
| 画廊 | `/` | 分页浏览所有作品 |
| 作品详情 | `/artwork/:id` | 查看图片、作者、标签 |
| 标签列表 | `/tags` | 所有标签及作品数 |
| 管理面板 | `/panel/:slug/` | 后台管理（需要 admin token） |

### 管理面板

通过 `/panel/<你的slug>/` 访问，首次进入会提示输入 admin token。

- **Artworks** — 作品列表、搜索、分页、删除、URL 导入（调用爬虫）
- **Artworks 编辑** — 修改标题/作者/标签/NSFW/AI 标记
- **Tags** — 创建、行内编辑（名称 + 类型）、删除

### Telegram Bot 命令

| 命令 | 权限 | 说明 |
|------|------|------|
| `/import <url> [#tag1 #tag2] [--post]` | 管理员 | 爬取 URL 导入作品，可选发布到频道 |
| `/post <artwork_id>` | 管理员 | 将已有作品发布到频道 |
| `/random` | 所有人 | 随机展示一个作品 |
| `/help` | 所有人 | 显示帮助信息 |

### 爬虫支持

| 平台 | 方式 | 说明 |
|------|------|------|
| Pixiv | Ajax API | 支持 `pixiv.net`、`phixiv.net` 链接 |
| Twitter/X | fxtwitter API | 支持 `twitter.com`、`x.com`、`fxtwitter.com`、`vxtwitter.com` 等 |
| 其他平台 | gallery-dl | 通用回退，需系统安装 gallery-dl |

导入流程：URL → 匹配爬虫 → 抓取元数据和图片 → 去重检查 → 存入数据库。

### API 路由

**公开接口**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/artworks` | 分页列表 (`?tag=&platform=&q=&page=&page_size=`) |
| GET | `/api/artworks/:id` | 作品详情 |
| GET | `/api/artworks/random` | 随机作品 |
| GET | `/api/tags` | 标签列表 (`?type=`) |
| GET | `/api/tags/:name` | 标签详情 |
| GET | `/api/tags/:name/artworks` | 标签下的作品 |

**管理接口**（需要 `X-Admin-Token` header）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/admin/artworks` | 创建作品 |
| POST | `/api/admin/artworks/import` | URL 导入作品（爬虫） |
| PUT | `/api/admin/artworks/:id` | 更新作品 |
| DELETE | `/api/admin/artworks/:id` | 删除作品 |
| POST | `/api/admin/tags` | 创建标签 |
| PUT | `/api/admin/tags/:id` | 更新标签 |
| DELETE | `/api/admin/tags/:id` | 删除标签 |

## 数据库

5 张表，标签已规范化：

- **artworks** — 核心实体，`platform + pid` 唯一约束用于去重
- **artwork_images** — 每页图片记录（原图 URL、缩略图、存储路径、Telegram file_id）
- **tags** — 标签实体，支持 `general/character/artist/meta` 类型和别名合并
- **artwork_tags** — 多对多关联表
- **bot_post_logs** — Bot 发布记录，支持多 Bot 多频道

## 开发命令速查

```bash
# 后端
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload              # 开发服务器
alembic upgrade head                       # 执行迁移
alembic revision --autogenerate -m "msg"   # 生成迁移
ruff check . && ruff format .              # lint + 格式化
mypy app/                                  # 类型检查

# 前端
cd frontend
pnpm dev          # 开发服务器
pnpm build        # 生产构建
pnpm lint         # ESLint 检查
```

## 许可证

本项目采用双重许可：

| 用途 | 适用许可证 |
|------|-----------|
| 个人学习、研究、非商业部署 | [PolyForm Noncommercial License 1.0.0](LICENSE) |
| 商业用途（含广告盈利、付费服务等） | [商业许可证](LICENSE-COMMERCIAL.md)（需单独获取） |

> **商业用途须获得额外授权**，即使公开了修改后的源码亦然。
> 如需商业授权，请通过 [Issues](https://github.com/hyacine/hyacine_gallery/issues) 联系。
