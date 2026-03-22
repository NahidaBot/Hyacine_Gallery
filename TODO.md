# Hyacine Gallery — 优化路线图

> 最后更新：2026-03-22

---

## 优先级说明

- 🔴 **高优先级** — 影响核心体验，尽快实现
- 🟡 **中优先级** — 重要但不紧急
- 🟢 **低优先级 / 长期** — 有价值，时机成熟再做

---

## 一、前端

### 🔴 交互体验优化

- [ ] **导入时自动读取剪贴板** — 管理面板导入框 focus 时自动填入剪贴板中的 URL，减少手动粘贴操作
- [ ] **标签别名/合并 UI** — 数据库已有 `alias_of_id` 字段，但管理面板缺少对应的合并/别名编辑界面

### 🟡 新页面

- [ ] **关于页面 `/about`** — 项目简介、技术栈、作者信息、开源协议
- [ ] **友情链接页面 `/links`** — 展示友链，支持管理面板增删

### 🟡 搜索与筛选

- [ ] **按作者筛选** — 画廊主页/搜索框支持 `author:用户名` 语法或独立的作者过滤器
- [ ] **作者主页 `/author/:name`** — 展示同一作者的所有作品，类似标签页

### 🟢 体验细节

- [ ] **图片懒加载占位符优化** — 使用主色调 blur placeholder（Next.js `blurDataURL`）
- [ ] **RSS/Atom Feed** — `/feed.xml`，让用户通过 RSS 阅读器订阅图库更新
- [ ] **键盘导航** — 作品详情页左右键切换上一张/下一张

---

## 二、后端

### 🔴 查重重构

- [ ] **基于 pHash 相似度的查重** — 当前查重依赖 `platform + pid` 精确匹配，应改为先做 pHash 汉明距离查询（阈值 ≤ 10），再精确去重，避免跨平台转载漏检

### 🟡 作者系统

- [ ] **`authors` 表** — 独立的作者实体，字段：`name`、`platform`、`platform_uid`、`canonical_id`（自引用，用于关联同一作者的多平台账号）
- [ ] **跨平台作者关联** — 管理面板支持将 Pixiv 用户、Twitter 用户等标记为"同一人"
- [ ] **作者 API** — `GET /api/authors`、`GET /api/authors/:id/artworks`

### 🟡 搜索增强

- [ ] **全文搜索** — 对 `title`、`description` 建立 FTS（SQLite FTS5 / PostgreSQL `tsvector`），支持 `q=` 参数关键词搜索
- [ ] **组合过滤** — 同时支持 `tag=` + `author=` + `platform=` + `q=` 多条件 AND 查询

### 🟡 爬虫扩展

- [ ] **BiliBili 动态爬虫** — 抓取 B 站图文动态（已有 `miyoushe.py`，可参照结构）
- [ ] **订阅式自动拉取** — 定时任务（APScheduler）订阅指定 Pixiv 用户/标签，自动入库新作品

### 🟢 安全与运维

- [ ] **API 限流** — 对公开接口加 `slowapi` 速率限制，防止滥用
- [ ] **导出功能** — 管理员可导出全部元数据为 JSON/CSV（运营备份用）
- [ ] **Webhook 支持** — 新作品入库后触发可配置的 Webhook，方便接入外部系统

---

## 三、Telegram Bot

### 🔴 发图后交互反馈

- [ ] **发图后 Inline Button** — `/post` 完成后，在反馈消息下方附加 `[跳转频道]` 按钮（`InlineKeyboardButton` + `url=channel_link`），方便管理员确认发布效果

### 🟡 LLM 集成

- [ ] **自动生成标签** — 调用 Claude API 对图片进行视觉理解，自动建议标签（管理员确认后写入）
- [ ] **标题/简介润色** — 对爬取到的标题提供中文翻译/优化建议
- [ ] **自然语言查询** — Bot 支持 `/search 金发女孩 魔法少女` 类语义搜索（结合 embedding）

### 🟡 Telegram OAuth 登录

- [ ] **前端管理面板接入 Telegram Login Widget** — 管理员通过 TG OAuth 免密码登录，替换当前 `X-Admin-Token` 静态 token 方案
- [ ] **Bot 侧验证** — Bot 命令鉴权改为查询 `users` 表，而非硬编码 `ADMIN_IDS`

### 🟢 长期规划

- [ ] **小程序适配** — 小程序前端（画饼，架构预留接口即可）

---

## 四、用户与权限系统重构

> 当前系统使用单一静态 token，长期应升级为完整的多用户体系。

### 🔴 设计目标

- **`users` 表** — `id`、`tg_id`、`tg_username`、`role`（`owner` / `admin`）、`created_at`
- **`owner`（站长）** — 完整权限：管理用户、配置 Bot、删除作品、管理标签
- **`admin`（管理员）** — 受限权限：导入作品、发图、编辑标签；不可管理用户或 Bot

### 🟡 实现步骤

1. [ ] 新增 `users` 表 + Alembic migration
2. [ ] 后端鉴权中间件改为查库（JWT 或 Session）
3. [ ] 前端管理面板集成 Telegram Login Widget（OAuth）
4. [ ] Bot 命令鉴权改为查 `users` 表
5. [ ] 管理面板增加用户管理页（仅 `owner` 可见）

---

## 五、我的额外建议

### 🟡 图片处理管道完善

- [ ] **WebP 自动转换** — 存储时生成 WebP 版本，前端优先加载，减少流量（已有缩略图生成管道，可在此扩展）
- [ ] **NSFW 自动检测** — 集成轻量模型（如 `open-nsfw2`）对新导入图片打分，自动设置 `is_nsfw` 标志

### 🟡 数据质量

- [ ] **重复标签检测** — 定期扫描标签相似度（编辑距离），提示管理员合并近似标签（如 `魔法少女` vs `魔法少女系`）
- [ ] **悬空图片清理** — 定期检查 `artwork_images` 中存储路径已删除但记录仍存在的孤儿记录

### 🟢 可观测性

- [ ] **管理面板数据看板** — 展示：总作品数、本周新增、最活跃标签、存储占用、Bot 发图频次
- [ ] **Bot 发图日志页** — 前端 `bot_post_logs` 可视化，了解哪些作品被发出去了

---

## 已完成 ✅

- 项目骨架（backend/frontend/bot/docker-compose）
- 数据库模型（标准化标签系统 + Alembic 迁移）
- 服务层（作品/标签 CRUD）
- API 路由（公开 + 管理 + 导入）
- 爬虫（Pixiv、Twitter、gallery-dl 兜底）
- 前端画廊（列表、详情、标签页）
- 前端管理面板（作品/标签 CRUD、URL 导入）
- Telegram Bot（import/post/random 命令）
- 图片存储服务（本地 + S3）+ TTL 清理
- pHash 相似图搜索
- Pixiv 标签中文优先策略
- Bot 发图 Telegram 文件 ID 缓存
