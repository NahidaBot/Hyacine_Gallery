import Link from "next/link";
import type { Artwork } from "@/types";

interface ArtworkCardProps {
  artwork: Artwork;
}

export function ArtworkCard({ artwork }: ArtworkCardProps) {
  const thumb =
    artwork.images[0]?.url_thumb || artwork.images[0]?.url_original || "";

  return (
    <Link
      href={`/artwork/${artwork.id}`}
      className="group overflow-hidden rounded-lg border border-neutral-200 transition-shadow hover:shadow-md dark:border-neutral-800"
    >
      <div className="relative aspect-square bg-neutral-100 dark:bg-neutral-900">
        {thumb ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={thumb}
            alt={artwork.title || `${artwork.platform} ${artwork.pid}`}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-neutral-300">
            No image
          </div>
        )}
        {artwork.is_nsfw && (
          <span className="absolute right-1 top-1 rounded bg-red-600 px-1.5 py-0.5 text-xs text-white">
            NSFW
          </span>
        )}
      </div>
      <div className="p-2">
        <p className="truncate text-sm font-medium">
          {artwork.title || artwork.pid}
        </p>
        <p className="truncate text-xs text-neutral-500">{artwork.author}</p>
      </div>
    </Link>
  );
}
