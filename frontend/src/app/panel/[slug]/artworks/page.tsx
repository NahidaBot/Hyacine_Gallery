"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { Artwork, ArtworkListResponse, ImportResponse, SimilarArtworkInfo } from "@/types";
import {
  adminDeleteArtwork,
  adminFetchArtworks,
  adminImportArtwork,
  adminMergeArtwork,
} from "@/lib/admin-api";

export default function ArtworksPage() {
  const { slug } = useParams<{ slug: string }>();
  const base = `/panel/${slug}`;

  const [artworks, setArtworks] = useState<Artwork[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  // 导入弹窗
  const [showImport, setShowImport] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const [importTags, setImportTags] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const [importResult, setImportResult] = useState<ImportResponse | null>(null);

  const pageSize = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data: ArtworkListResponse = await adminFetchArtworks({
        page,
        pageSize,
        q: search || undefined,
      });
      setArtworks(data.data);
      setTotal(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDelete(id: number) {
    if (!confirm(`确认删除作品 #${id}？`)) return;
    try {
      await adminDeleteArtwork(id);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  async function handleImport(autoMerge = false) {
    if (!importUrl.trim()) return;
    setImporting(true);
    setImportError("");
    setImportResult(null);
    try {
      const tags = importTags
        .split(",")
        .map((t) => t.replace(/^#/, "").trim())
        .filter(Boolean);
      const result = await adminImportArtwork(importUrl.trim(), tags, autoMerge);
      setImportResult(result);

      // 如果没有相似候选，关闭弹窗并刷新
      if (!result.similar?.length) {
        setShowImport(false);
        setImportUrl("");
        setImportTags("");
        setImportResult(null);
        await load();
      }
    } catch (err) {
      setImportError(String(err));
    } finally {
      setImporting(false);
    }
  }

  async function handleMergeCandidate(candidate: SimilarArtworkInfo) {
    if (!importResult?.artwork) return;
    try {
      // 合并：保留页数更多的作品
      const newId = importResult.artwork.id;
      if (importResult.artwork.page_count <= candidate.artwork_id) {
        // 近似判断；后端合并接口会处理页数比较
        await adminMergeArtwork(candidate.artwork_id, newId);
      } else {
        await adminMergeArtwork(newId, candidate.artwork_id);
      }
      setShowImport(false);
      setImportUrl("");
      setImportTags("");
      setImportResult(null);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  function closeImport() {
    setShowImport(false);
    setImportUrl("");
    setImportTags("");
    setImportError("");
    setImportResult(null);
  }

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">作品管理</h1>
        <button
          onClick={() => setShowImport(true)}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          导入
        </button>
      </div>

      {/* 搜索 */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="按标题或作者搜索..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
      </div>

      {/* 导入弹窗 */}
      {showImport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="mx-4 w-full max-w-lg rounded-lg bg-white p-6 dark:bg-neutral-900">
            <h2 className="mb-4 text-lg font-bold">导入作品</h2>

            {/* 发现相似作品 */}
            {importResult?.similar?.length ? (
              <div>
                <p className="mb-2 text-sm text-yellow-600 dark:text-yellow-400">
                  {importResult.message}
                </p>
                <p className="mb-3 text-sm text-neutral-500">
                  已导入为 #{importResult.artwork?.id}，发现以下相似作品：
                </p>
                <div className="mb-4 space-y-2">
                  {importResult.similar.map((s) => (
                    <div
                      key={s.artwork_id}
                      className="flex items-center gap-3 rounded border border-neutral-200 p-2 dark:border-neutral-700"
                    >
                      {s.thumb_url && (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={s.thumb_url}
                          alt=""
                          className="h-12 w-12 rounded object-cover"
                        />
                      )}
                      <div className="flex-1 text-sm">
                        <p className="font-medium">
                          #{s.artwork_id} — {s.title || s.pid}
                        </p>
                        <p className="text-xs text-neutral-500">
                          {s.platform}/{s.pid} · 距离: {s.distance}
                        </p>
                      </div>
                      <button
                        onClick={() => handleMergeCandidate(s)}
                        className="rounded bg-orange-600 px-3 py-1 text-xs font-medium text-white hover:bg-orange-700"
                      >
                        合并
                      </button>
                    </div>
                  ))}
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => {
                      // 保留为独立作品
                      closeImport();
                      load();
                    }}
                    className="rounded px-4 py-2 text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800"
                  >
                    保留独立
                  </button>
                </div>
              </div>
            ) : (
              <>
                <label className="mb-1 block text-sm font-medium">链接</label>
                <input
                  type="url"
                  value={importUrl}
                  onChange={(e) => setImportUrl(e.target.value)}
                  placeholder="https://www.pixiv.net/artworks/..."
                  className="mb-3 w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800"
                />
                <label className="mb-1 block text-sm font-medium">
                  标签（逗号分隔）
                </label>
                <input
                  type="text"
                  value={importTags}
                  onChange={(e) => setImportTags(e.target.value)}
                  placeholder="风景, 背景"
                  className="mb-4 w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800"
                />
                {importError && (
                  <p className="mb-3 text-sm text-red-500">{importError}</p>
                )}
                <div className="flex justify-end gap-2">
                  <button
                    onClick={closeImport}
                    className="rounded px-4 py-2 text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800"
                  >
                    取消
                  </button>
                  <button
                    onClick={() => handleImport(false)}
                    disabled={importing}
                    className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {importing ? "导入中..." : "导入"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* 列表 */}
      {loading ? (
        <p className="text-sm text-neutral-400">加载中...</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-neutral-200 text-xs uppercase text-neutral-500 dark:border-neutral-700">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">缩略图</th>
                  <th className="px-3 py-2">标题</th>
                  <th className="px-3 py-2">作者</th>
                  <th className="px-3 py-2">平台</th>
                  <th className="px-3 py-2">来源</th>
                  <th className="px-3 py-2">标签</th>
                  <th className="px-3 py-2">标记</th>
                  <th className="px-3 py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {artworks.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-neutral-100 dark:border-neutral-800"
                  >
                    <td className="px-3 py-2 tabular-nums">{a.id}</td>
                    <td className="px-3 py-2">
                      {a.images[0] ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={
                            a.images[0].url_thumb || a.images[0].url_original
                          }
                          alt=""
                          className="h-10 w-10 rounded object-cover"
                        />
                      ) : (
                        <span className="text-neutral-300">-</span>
                      )}
                    </td>
                    <td className="max-w-48 truncate px-3 py-2">
                      <Link
                        href={`${base}/artworks/${a.id}`}
                        className="hover:underline"
                      >
                        {a.title || a.pid}
                      </Link>
                    </td>
                    <td className="max-w-32 truncate px-3 py-2">{a.author}</td>
                    <td className="px-3 py-2">{a.platform}</td>
                    <td className="px-3 py-2 text-xs text-neutral-500">
                      {(a.sources?.length ?? 0) > 1
                        ? `${a.sources.length} 个来源`
                        : a.platform}
                    </td>
                    <td className="max-w-40 truncate px-3 py-2 text-xs text-neutral-500">
                      {a.tags.map((t) => `#${t.name}`).join(" ")}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {a.is_nsfw && (
                        <span className="mr-1 rounded bg-red-100 px-1.5 py-0.5 text-red-600 dark:bg-red-900/30">
                          NSFW
                        </span>
                      )}
                      {a.is_ai && (
                        <span className="rounded bg-purple-100 px-1.5 py-0.5 text-purple-600 dark:bg-purple-900/30">
                          AI
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        <Link
                          href={`${base}/artworks/${a.id}`}
                          className="text-blue-600 hover:underline"
                        >
                          编辑
                        </Link>
                        <button
                          onClick={() => handleDelete(a.id)}
                          className="text-red-500 hover:underline"
                        >
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {artworks.length === 0 && (
                  <tr>
                    <td
                      colSpan={9}
                      className="px-3 py-8 text-center text-neutral-400"
                    >
                      暂无作品。
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between text-sm">
              <span className="text-neutral-500">
                第 {page} / {totalPages} 页（共 {total} 条）
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="rounded border border-neutral-300 px-3 py-1 disabled:opacity-30 dark:border-neutral-700"
                >
                  上一页
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="rounded border border-neutral-300 px-3 py-1 disabled:opacity-30 dark:border-neutral-700"
                >
                  下一页
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
