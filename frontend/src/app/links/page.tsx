import { fetchLinks } from "@/lib/api";

export const metadata = {
  title: "友情链接 — Hyacine Gallery",
};

export const dynamic = "force-dynamic";

export default async function LinksPage() {
  const links = await fetchLinks().catch(() => []);

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="mb-2 text-3xl font-bold">友情链接</h1>
      <p className="mb-8 text-neutral-500 dark:text-neutral-400">
        朋友们的站点，欢迎互换链接。
      </p>

      {links.length === 0 ? (
        <p className="text-neutral-400">暂无友情链接。</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {links.map((link) => (
            <a
              key={link.id}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center gap-4 rounded-xl border border-neutral-200 p-4 transition-colors hover:border-neutral-400 dark:border-neutral-800 dark:hover:border-neutral-600"
            >
              {link.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={link.avatar_url}
                  alt={link.name}
                  className="h-12 w-12 rounded-full object-cover"
                />
              ) : (
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-neutral-100 text-lg font-bold text-neutral-400 dark:bg-neutral-800">
                  {link.name.charAt(0).toUpperCase()}
                </div>
              )}
              <div className="min-w-0">
                <p className="font-medium group-hover:underline">{link.name}</p>
                {link.description && (
                  <p className="mt-0.5 truncate text-sm text-neutral-500 dark:text-neutral-400">
                    {link.description}
                  </p>
                )}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
