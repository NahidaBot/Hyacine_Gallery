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

  const images = JSON.parse(artwork.images_json) as string[];

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-2 text-2xl font-bold">
        {artwork.title || `${artwork.platform} #${artwork.pid}`}
      </h1>
      <p className="mb-6 text-sm text-neutral-500">
        by {artwork.author || "Unknown"} · {artwork.platform}
        {artwork.source_url && (
          <>
            {" · "}
            <a
              href={artwork.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
            >
              Source
            </a>
          </>
        )}
      </p>

      <div className="space-y-4">
        {images.map((url, i) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={i}
            src={url}
            alt={`${artwork.title || artwork.pid} page ${i + 1}`}
            className="w-full rounded-lg"
            loading="lazy"
          />
        ))}
      </div>

      {artwork.tags.length > 0 && (
        <div className="mt-6 flex flex-wrap gap-2">
          {artwork.tags.map((tag) => (
            <a
              key={tag}
              href={`/tags/${encodeURIComponent(tag)}`}
              className="rounded-full bg-neutral-100 px-3 py-1 text-sm hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700"
            >
              #{tag}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
