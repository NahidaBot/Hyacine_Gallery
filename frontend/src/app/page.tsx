import { fetchArtworks } from "@/lib/api";
import { ArtworkGrid } from "@/components/gallery/ArtworkGrid";

export const dynamic = "force-dynamic";

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ tag?: string; platform?: string; q?: string; page?: string }>;
}) {
  const params = await searchParams;
  const page = Number(params.page) || 1;

  const { data: artworks, total } = await fetchArtworks({
    page,
    tag: params.tag,
    platform: params.platform,
    q: params.q,
  });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Gallery</h1>
      <p className="mb-4 text-sm text-neutral-500">
        {total} artworks
        {params.tag && <> tagged <strong>#{params.tag}</strong></>}
        {params.q && <> matching <strong>&ldquo;{params.q}&rdquo;</strong></>}
      </p>
      <ArtworkGrid artworks={artworks} />
    </div>
  );
}
