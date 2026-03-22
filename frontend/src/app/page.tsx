import { fetchArtworks } from "@/lib/api";
import { ArtworkGrid } from "@/components/gallery/ArtworkGrid";

export const dynamic = "force-dynamic";

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{
    tag?: string;
    platform?: string;
    q?: string;
    page?: string;
    author_name?: string;
  }>;
}) {
  const params = await searchParams;
  const page = Number(params.page) || 1;

  // 解析 q 中 author:xxx 语法
  let q = params.q;
  let authorName = params.author_name;
  if (q) {
    const authorMatch = q.match(/author:(\S+)/);
    if (authorMatch) {
      authorName = authorMatch[1];
      q = q.replace(/author:\S+/, "").trim() || undefined;
    }
  }

  const { data: artworks, total } = await fetchArtworks({
    page,
    tag: params.tag,
    platform: params.platform,
    q,
    authorName,
  });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">画廊</h1>
      <p className="mb-4 text-sm text-neutral-500">
        共 {total} 件作品
        {params.tag && <> 标签 <strong>#{params.tag}</strong></>}
        {authorName && <> 作者 <strong>{authorName}</strong></>}
        {(q || params.q) && <> 搜索 <strong>&ldquo;{q || params.q}&rdquo;</strong></>}
      </p>
      <ArtworkGrid artworks={artworks} />
    </div>
  );
}
