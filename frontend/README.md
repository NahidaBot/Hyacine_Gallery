# Hyacine Gallery 前端

基于 Next.js 16 (App Router) + TypeScript + Tailwind CSS 4 的画廊前端。

## 开发

```bash
pnpm install
pnpm dev          # 开发服务器 http://localhost:3000
pnpm build        # 生产构建
pnpm lint         # ESLint 检查
```

## 环境变量

在 `.env.local` 或项目根 `.env` 中配置：

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 页面

| 路径 | 说明 |
|------|------|
| `/` | 画廊首页，分页浏览作品 |
| `/artwork/:id` | 作品详情页 |
| `/tags` | 标签列表 |
| `/panel/:slug/` | 管理面板入口 |
| `/panel/:slug/artworks` | 作品管理（列表、搜索、导入、删除） |
| `/panel/:slug/artworks/:id` | 作品编辑（标题、作者、标签、标记） |
| `/panel/:slug/tags` | 标签管理（创建、编辑、删除） |

## 管理面板

访问 `/panel/<slug>/`，首次进入会提示输入 admin token（与后端 `ADMIN_TOKEN` 一致）。Token 保存在 localStorage，可在侧边栏点击"Change token"更换。
