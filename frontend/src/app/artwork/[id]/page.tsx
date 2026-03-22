import { fetchArtwork } from "@/lib/api";
import { notFound } from "next/navigation";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function ArtworkPage({ params }: Props) {
  const { id } = await params;
  const artworkId = Number(id);
  if (Number.isNaN(artworkId)) notFound();

  let artwork;
  try {
    artwork = await fetchArtwork(artworkId);
  } catch {
    notFound();
  }

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-2 text-2xl font-bold">
        {artwork.title_zh || artwork.title || `${artwork.platform} #${artwork.pid}`}
      </h1>
      <p className="mb-6 text-sm text-neutral-500">
        作者 {artwork.author || "未知"} · {artwork.platform}
        {artwork.source_url && (
          <>
            {" · "}
            <a
              href={artwork.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
            >
              来源
            </a>
          </>
        )}
      </p>

      <div className="space-y-4">
        {artwork.images.map((img) => (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            key={img.id}
            src={img.url_original}
            alt={`${artwork.title || artwork.pid} 第 ${img.page_index + 1} 页`}
            className="w-full rounded-lg"
            loading="lazy"
          />
        ))}
      </div>

      {artwork.tags.length > 0 && (
        <div className="mt-6 flex flex-wrap gap-2">
          {artwork.tags.map((tag) => (
            <a
              key={tag.id}
              href={`/tags/${encodeURIComponent(tag.name)}`}
              className="rounded-full bg-neutral-100 px-3 py-1 text-sm hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700"
            >
              #{tag.name}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
