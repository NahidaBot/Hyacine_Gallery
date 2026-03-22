import { fetchAuthorByName, fetchAuthorArtworks } from "@/lib/api";
import { ArtworkGrid } from "@/components/gallery/ArtworkGrid";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function AuthorPage({
  params,
  searchParams,
}: {
  params: Promise<{ name: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { name } = await params;
  const { page: pageStr } = await searchParams;
  const page = Number(pageStr) || 1;
  const decodedName = decodeURIComponent(name);

  let author;
  try {
    author = await fetchAuthorByName(decodedName);
  } catch {
    notFound();
  }

  const { data: artworks, total } = await fetchAuthorArtworks(author.id, {
    page,
  });

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold">{author.name}</h1>
      <p className="mb-6 text-sm text-neutral-500">
        {author.platform}
        {author.platform_uid && ` · ${author.platform_uid}`}
        {" · "}共 {total} 件作品
      </p>
      <ArtworkGrid artworks={artworks} />
    </div>
  );
}
