import Link from "next/link";
import type { Artwork } from "@/types";

interface ArtworkCardProps {
  artwork: Artwork;
}

export function ArtworkCard({ artwork }: ArtworkCardProps) {
  // TODO: replace with real thumbnail URL from images_json
  const images = JSON.parse(artwork.images_json) as string[];
  const thumb = images[0] ?? "/placeholder.svg";

  return (
    <Link
      href={`/artwork/${artwork.id}`}
      className="group overflow-hidden rounded-lg border border-neutral-200 transition-shadow hover:shadow-md dark:border-neutral-800"
    >
      <div className="relative aspect-square bg-neutral-100 dark:bg-neutral-900">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={thumb}
          alt={artwork.title || `${artwork.platform} ${artwork.pid}`}
          className="h-full w-full object-cover transition-transform group-hover:scale-105"
          loading="lazy"
        />
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
