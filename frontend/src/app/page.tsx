import { fetchArtworks } from "@/lib/api";
import { ArtworkGrid } from "@/components/gallery/ArtworkGrid";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const { data: artworks, total } = await fetchArtworks({ page: 1 });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Gallery</h1>
      <p className="mb-4 text-sm text-neutral-500">{total} artworks</p>
      <ArtworkGrid artworks={artworks} />
    </div>
  );
}
