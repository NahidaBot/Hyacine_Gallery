"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import type { Artwork } from "@/types";
import {
  adminAddSource,
  adminDeleteArtwork,
  adminDeleteArtworkImage,
  adminDeleteSource,
  adminFetchArtwork,
  adminMergeArtwork,
  adminUpdateArtwork,
} from "@/lib/admin-api";

export default function ArtworkEditPage() {
  const { slug, id } = useParams<{ slug: string; id: string }>();
  const router = useRouter();
  const base = `/panel/${slug}`;
  const artworkId = Number(id);

  const [artwork, setArtwork] = useState<Artwork | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // 表单状态
  const [title, setTitle] = useState("");
  const [titleZh, setTitleZh] = useState("");
  const [author, setAuthor] = useState("");
  const [isNsfw, setIsNsfw] = useState(false);
  const [isAi, setIsAi] = useState(false);
  const [tagsInput, setTagsInput] = useState("");

  // 添加来源
  const [showAddSource, setShowAddSource] = useState(false);
  const [sourceUrl, setSourceUrl] = useState("");
  const [addingSource, setAddingSource] = useState(false);

  // 合并
  const [showMerge, setShowMerge] = useState(false);
  const [mergeId, setMergeId] = useState("");
  const [merging, setMerging] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminFetchArtwork(artworkId);
      setArtwork(data);
      setTitle(data.title);
      setTitleZh(data.title_zh);
      setAuthor(data.author);
      setIsNsfw(data.is_nsfw);
      setIsAi(data.is_ai);
      setTagsInput(data.tags.map((t) => t.name).join(", "));
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [artworkId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const tags = tagsInput
        .split(",")
        .map((t) => t.replace(/^#/, "").trim())
        .filter(Boolean);
      const updated = await adminUpdateArtwork(artworkId, {
        title,
        title_zh: titleZh,
        author,
        is_nsfw: isNsfw,
        is_ai: isAi,
        tags,
      });
      setArtwork(updated);
      setTagsInput(updated.tags.map((t) => t.name).join(", "));
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`确认删除作品 #${artworkId}？此操作不可撤销。`))
      return;
    try {
      await adminDeleteArtwork(artworkId);
      router.push(`${base}/artworks`);
    } catch (err) {
      alert(String(err));
    }
  }

  async function handleAddSource() {
    if (!sourceUrl.trim()) return;
    setAddingSource(true);
    try {
      await adminAddSource(artworkId, sourceUrl.trim());
      setShowAddSource(false);
      setSourceUrl("");
      await load();
    } catch (err) {
      alert(String(err));
    } finally {
      setAddingSource(false);
    }
  }

  async function handleDeleteSource(sourceId: number) {
    if (!confirm("确认移除此来源？")) return;
    try {
      await adminDeleteSource(artworkId, sourceId);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  async function handleMerge() {
    const targetId = Number(mergeId);
    if (!targetId || targetId === artworkId) return;
    if (!confirm(`将作品 #${targetId} 合并到当前作品？#${targetId} 将被删除。`))
      return;
    setMerging(true);
    try {
      await adminMergeArtwork(artworkId, targetId);
      setShowMerge(false);
      setMergeId("");
      await load();
    } catch (err) {
      alert(String(err));
    } finally {
      setMerging(false);
    }
  }

  if (loading)
    return <p className="text-sm text-neutral-400">加载中...</p>;
  if (!artwork)
    return <p className="text-sm text-red-500">{error || "未找到"}</p>;

  const inputCls =
    "w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900";

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          编辑作品 #{artwork.id}
        </h1>
        <button
          onClick={handleDelete}
          className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          删除
        </button>
      </div>

      {/* 图片预览 */}
      <div className="mb-6 flex gap-2 overflow-x-auto">
        {artwork.images.map((img) => (
          <div key={img.id} className="group relative shrink-0">
            <a
              href={img.url_original}
              target="_blank"
              rel="noopener noreferrer"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={img.url_thumb || img.url_original}
                alt={`第 ${img.page_index + 1} 页`}
                className="h-32 rounded border border-neutral-200 object-cover dark:border-neutral-700"
              />
            </a>
            {artwork.images.length > 1 && (
              <button
                onClick={async () => {
                  if (!confirm(`确认删除第 ${img.page_index + 1} 页？`)) return;
                  try {
                    await adminDeleteArtworkImage(artworkId, img.id);
                    await load();
                  } catch (err) {
                    alert(String(err));
                  }
                }}
                className="absolute -right-1 -top-1 hidden size-5 items-center justify-center rounded-full bg-red-600 text-xs text-white hover:bg-red-700 group-hover:flex"
                title={`删除第 ${img.page_index + 1} 页`}
              >
                x
              </button>
            )}
            <span className="absolute bottom-1 left-1 rounded bg-black/60 px-1.5 py-0.5 text-[10px] text-white">
              {img.page_index + 1}
            </span>
          </div>
        ))}
      </div>

      {/* 来源 */}
      <div className="mb-6 rounded border border-neutral-200 p-4 dark:border-neutral-800">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold">来源</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setShowAddSource(!showAddSource)}
              className="text-xs text-blue-600 hover:underline"
            >
              + 添加来源
            </button>
            <button
              onClick={() => setShowMerge(!showMerge)}
              className="text-xs text-orange-600 hover:underline"
            >
              合并作品
            </button>
          </div>
        </div>

        {/* 来源列表 */}
        <div className="space-y-1">
          {artwork.sources?.map((s) => (
            <div
              key={s.id}
              className="flex items-center gap-2 text-sm"
            >
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                  s.is_primary
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                    : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
                }`}
              >
                {s.platform}
              </span>
              <span className="text-xs text-neutral-500">{s.pid}</span>
              {s.source_url && (
                <a
                  href={s.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:underline"
                >
                  链接
                </a>
              )}
              {s.is_primary && (
                <span className="text-[10px] text-neutral-400">主要</span>
              )}
              {!s.is_primary && (
                <button
                  onClick={() => handleDeleteSource(s.id)}
                  className="text-[10px] text-red-500 hover:underline"
                >
                  移除
                </button>
              )}
            </div>
          ))}
          {(!artwork.sources || artwork.sources.length === 0) && (
            <p className="text-xs text-neutral-400">暂无来源记录。</p>
          )}
        </div>

        {/* 添加来源表单 */}
        {showAddSource && (
          <div className="mt-3 flex gap-2">
            <input
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="https://twitter.com/..."
              className="flex-1 rounded border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            />
            <button
              onClick={handleAddSource}
              disabled={addingSource}
              className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {addingSource ? "..." : "添加"}
            </button>
          </div>
        )}

        {/* 合并表单 */}
        {showMerge && (
          <div className="mt-3 flex gap-2">
            <input
              type="number"
              value={mergeId}
              onChange={(e) => setMergeId(e.target.value)}
              placeholder="要合并的作品 ID"
              className="flex-1 rounded border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            />
            <button
              onClick={handleMerge}
              disabled={merging}
              className="rounded bg-orange-600 px-3 py-1 text-xs font-medium text-white hover:bg-orange-700 disabled:opacity-50"
            >
              {merging ? "..." : "合并"}
            </button>
          </div>
        )}
      </div>

      {/* 编辑表单 */}
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium">标题</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={inputCls}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">中文标题</label>
          <input
            type="text"
            value={titleZh}
            onChange={(e) => setTitleZh(e.target.value)}
            className={inputCls}
            placeholder="AI 自动翻译或手动填写"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">作者</label>
          <input
            type="text"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            className={inputCls}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">
            标签（逗号分隔）
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              className={`${inputCls} flex-1`}
            />
            <button
              type="button"
              onClick={async () => {
                try {
                  const res = await fetch(
                    `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/admin/artworks/${artworkId}/suggest-tags`,
                    {
                      method: "POST",
                      headers: {
                        Authorization: `Bearer ${localStorage.getItem("jwt_token") ?? ""}`,
                      },
                    },
                  );
                  if (!res.ok) throw new Error(await res.text());
                  const suggestions = await res.json();
                  if (suggestions.length === 0) {
                    alert("AI 未返回标签建议");
                    return;
                  }
                  const names = suggestions
                    .filter((s: { confidence: number }) => s.confidence >= 0.5)
                    .map((s: { name: string }) => s.name);
                  if (names.length > 0) {
                    const current = tagsInput
                      .split(",")
                      .map((t: string) => t.trim())
                      .filter(Boolean);
                    const merged = [
                      ...new Set([...current, ...names]),
                    ].join(", ");
                    setTagsInput(merged);
                  }
                } catch (e) {
                  alert(`AI 标签建议失败: ${e}`);
                }
              }}
              className="shrink-0 rounded bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700"
            >
              AI 建议
            </button>
          </div>
        </div>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isNsfw}
              onChange={(e) => setIsNsfw(e.target.checked)}
            />
            NSFW
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isAi}
              onChange={(e) => setIsAi(e.target.checked)}
            />
            AI 生成
          </label>
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "保存中..." : "保存"}
          </button>
          <button
            onClick={() => router.push(`${base}/artworks`)}
            className="rounded border border-neutral-300 px-6 py-2 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
          >
            返回
          </button>
        </div>
      </div>
    </div>
  );
}
