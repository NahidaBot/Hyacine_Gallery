export const metadata = {
  title: "关于 — Hyacine Gallery",
};

const TECH_STACK = [
  { category: "后端", items: ["Python 3.14+", "FastAPI", "SQLAlchemy (async)", "Alembic", "SQLite / PostgreSQL"] },
  { category: "前端", items: ["Next.js 16 (App Router)", "TypeScript", "Tailwind CSS 4", "React 19"] },
  { category: "Bot", items: ["python-telegram-bot", "Telegram Bot API"] },
  { category: "爬虫", items: ["Pixiv API", "fxtwitter API", "gallery-dl"] },
  { category: "部署", items: ["Docker Compose", "Nginx"] },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="mb-2 text-3xl font-bold">Hyacine Gallery</h1>
      <p className="mb-8 text-neutral-500 dark:text-neutral-400">
        一个私人图库，用于收藏来自 Pixiv、Twitter 等平台的插画作品。
      </p>

      <section className="mb-10">
        <h2 className="mb-4 text-xl font-semibold">功能简介</h2>
        <ul className="space-y-2 text-sm text-neutral-700 dark:text-neutral-300">
          <li>• 多平台作品导入（Pixiv、Twitter / X、Bilibili 等）</li>
          <li>• 标签系统 — 支持类型分组、别名合并</li>
          <li>• Telegram Bot 集成 — 导入、定时发图、发布队列</li>
          <li>• 管理面板 — 作品 CRUD、标签管理、Bot 频道配置</li>
          <li>• 以图搜图 — 基于感知哈希的相似作品检索</li>
          <li>• WebAuthn Passkey + Telegram OAuth 双轨登录</li>
        </ul>
      </section>

      <section className="mb-10">
        <h2 className="mb-4 text-xl font-semibold">技术栈</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {TECH_STACK.map(({ category, items }) => (
            <div key={category} className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
              <h3 className="mb-2 text-sm font-semibold text-neutral-500 dark:text-neutral-400">
                {category}
              </h3>
              <ul className="space-y-1">
                {items.map((item) => (
                  <li key={item} className="text-sm">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-10">
        <h2 className="mb-4 text-xl font-semibold">许可协议</h2>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          本项目采用{" "}
          <span className="font-medium text-neutral-900 dark:text-neutral-100">
            PolyForm Noncommercial License 1.0.0
          </span>{" "}
          发布——允许个人学习、研究及非营利用途的自由使用与修改。
          商业用途（SaaS、广告营收、付费产品等）需另行获取商业许可证，详情请联系站长。
        </p>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-semibold">版权声明</h2>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          图库中的所有作品版权归原作者所有。本站仅供个人收藏与欣赏使用，不用于任何商业目的。
          如有版权问题，请联系站长删除。
        </p>
      </section>
    </div>
  );
}
