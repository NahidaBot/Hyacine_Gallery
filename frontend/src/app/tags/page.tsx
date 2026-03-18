import { fetchTags } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TagsPage() {
  const tags = await fetchTags();

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Tags</h1>
      <div className="flex flex-wrap gap-3">
        {tags.map(({ tag, count }) => (
          <a
            key={tag}
            href={`/?tag=${encodeURIComponent(tag)}`}
            className="rounded-full bg-neutral-100 px-4 py-2 text-sm transition-colors hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700"
          >
            #{tag}
            <span className="ml-1.5 text-neutral-400">{count}</span>
          </a>
        ))}
        {tags.length === 0 && (
          <p className="text-neutral-400">No tags yet.</p>
        )}
      </div>
    </div>
  );
}
