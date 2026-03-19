"use client";

import type { Artwork } from "@/types";
import { useApp } from "@/components/providers/AppProvider";
import { ArtworkCard } from "./ArtworkCard";

interface ArtworkGridProps {
  artworks: Artwork[];
}

export function ArtworkGrid({ artworks }: ArtworkGridProps) {
  const { nsfwMode, aiMode, columns } = useApp();

  const filtered = artworks.filter((a) => {
    if (nsfwMode === "hide" && a.is_nsfw) return false;
    if (nsfwMode === "only" && !a.is_nsfw) return false;
    if (aiMode === "hide" && a.is_ai) return false;
    if (aiMode === "only" && !a.is_ai) return false;
    return true;
  });

  if (filtered.length === 0) {
    return (
      <p className="py-12 text-center text-neutral-400">
        {artworks.length > 0 ? "No artworks match the current filter." : "No artworks yet."}
      </p>
    );
  }

  return (
    <div className="gap-4" style={{ columnCount: columns }}>
      {filtered.map((artwork) => (
        <div key={artwork.id} className="mb-4 break-inside-avoid">
          <ArtworkCard artwork={artwork} />
        </div>
      ))}
    </div>
  );
}
