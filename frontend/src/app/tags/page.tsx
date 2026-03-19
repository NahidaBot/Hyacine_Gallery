import { fetchTags } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TagsPage() {
  const { data: tags } = await fetchTags();

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">标签</h1>
      <div className="flex flex-wrap gap-3">
        {tags.map(({ name, artwork_count }) => (
          <a
            key={name}
            href={`/?tag=${encodeURIComponent(name)}`}
            className="rounded-full bg-neutral-100 px-4 py-2 text-sm transition-colors hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700"
          >
            #{name}
            <span className="ml-1.5 text-neutral-400">{artwork_count}</span>
          </a>
        ))}
        {tags.length === 0 && (
          <p className="text-neutral-400">暂无标签。</p>
        )}
      </div>
    </div>
  );
}
