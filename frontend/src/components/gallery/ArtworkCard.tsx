import Link from "next/link";
import type { Artwork } from "@/types";

interface ArtworkCardProps {
  artwork: Artwork;
}

const THUMB_MAX_EDGE = 1536;

export function ArtworkCard({ artwork }: ArtworkCardProps) {
  const img = artwork.images[0];
  const thumb = img?.url_thumb || "";
  const original = img?.url_original || "";
  const src = thumb || original;

  // Compute thumb width for srcSet descriptor
  const origW = img?.width || 0;
  const origH = img?.height || 0;
  const longEdge = Math.max(origW, origH);
  const thumbW = longEdge > THUMB_MAX_EDGE
    ? Math.round(origW * (THUMB_MAX_EDGE / longEdge))
    : origW;

  // Build srcSet: let browser pick thumb vs original based on rendered width
  const srcSet =
    thumb && original && thumb !== original && thumbW > 0 && origW > thumbW
      ? `${thumb} ${thumbW}w, ${original} ${origW}w`
      : undefined;

  const hasBadges = artwork.is_nsfw || artwork.is_ai;

  return (
    <Link
      href={`/artwork/${artwork.id}`}
      className="group inline-block w-full overflow-hidden rounded-lg border border-neutral-200 transition-shadow hover:shadow-md dark:border-neutral-800"
    >
      <div className="relative w-full overflow-hidden bg-neutral-100 dark:bg-neutral-900">
        {src ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={src}
            srcSet={srcSet}
            sizes="100vw"
            alt={artwork.title || `${artwork.platform} ${artwork.pid}`}
            className="block w-full transition-transform group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex aspect-square items-center justify-center text-neutral-300">
            No image
          </div>
        )}
        {hasBadges && (
          <div className="absolute right-1 top-1 flex gap-1">
            {artwork.is_nsfw && (
              <span className="rounded bg-red-600/80 px-1.5 py-0.5 text-[10px] font-medium text-white">
                NSFW
              </span>
            )}
            {artwork.is_ai && (
              <span className="rounded bg-blue-600/80 px-1.5 py-0.5 text-[10px] font-medium text-white">
                AI
              </span>
            )}
          </div>
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
