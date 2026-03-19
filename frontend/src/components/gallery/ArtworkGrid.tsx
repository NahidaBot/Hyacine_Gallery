"use client";

import type { Artwork } from "@/types";
import { useApp } from "@/components/providers/AppProvider";
import { ArtworkCard } from "./ArtworkCard";

interface ArtworkGridProps {
  artworks: Artwork[];
}

export function ArtworkGrid({ artworks }: ArtworkGridProps) {
  const { nsfwMode } = useApp();

  const filtered = artworks.filter((a) => {
    if (nsfwMode === "hide") return !a.is_nsfw;
    if (nsfwMode === "only") return a.is_nsfw;
    return true; // "show"
  });

  if (filtered.length === 0) {
    return (
      <p className="py-12 text-center text-neutral-400">
        {artworks.length > 0 ? "No artworks match the current filter." : "No artworks yet."}
      </p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {filtered.map((artwork) => (
        <ArtworkCard key={artwork.id} artwork={artwork} />
      ))}
    </div>
  );
}
