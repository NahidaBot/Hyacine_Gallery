"use client";

import { useCallback, useEffect, useState } from "react";
import type { Author } from "@/types";
import {
  adminFetchAuthors,
  adminUpdateAuthor,
  adminDeleteAuthor,
} from "@/lib/admin-api";

export default function AuthorsPage() {
  const [authors, setAuthors] = useState<Author[]>([]);
  const [loading, setLoading] = useState(true);
  const [platform, setPlatform] = useState("");
  const [mergeTarget, setMergeTarget] = useState<{
    id: number;
    canonicalId: string;
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminFetchAuthors(platform || undefined);
      setAuthors(data);
    } finally {
      setLoading(false);
    }
  }, [platform]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleLink(authorId: number, canonicalId: number) {
    await adminUpdateAuthor(authorId, { canonical_id: canonicalId });
    setMergeTarget(null);
    load();
  }

  async function handleUnlink(authorId: number) {
    await adminUpdateAuthor(authorId, { canonical_id: null });
    load();
  }

  async function handleDelete(authorId: number) {
    if (!confirm("确定删除此作者？")) return;
    await adminDeleteAuthor(authorId);
    load();
  }

  // 按 canonical 分组
  const groups = new Map<number, Author[]>();
  for (const a of authors) {
    const key = a.canonical_id ?? a.id;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(a);
  }

  const platforms = [...new Set(authors.map((a) => a.platform))].sort();

  return (
    <div>
      <h1 className="mb-4 text-xl font-bold">作者管理</h1>

      <div className="mb-4 flex items-center gap-2">
        <select
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          className="rounded border px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-800"
        >
          <option value="">全部平台</option>
          {platforms.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <span className="text-sm text-neutral-500">
          共 {authors.length} 位作者
        </span>
      </div>

      {loading ? (
        <p className="text-neutral-500">加载中...</p>
      ) : (
        <div className="space-y-2">
          {[...groups.entries()].map(([canonicalId, members]) => (
            <div
              key={canonicalId}
              className={`rounded border p-3 ${members.length > 1 ? "border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30" : "border-neutral-200 dark:border-neutral-700"}`}
            >
              {members.length > 1 && (
                <p className="mb-2 text-xs font-medium text-blue-600 dark:text-blue-400">
                  关联组 #{canonicalId}
                </p>
              )}
              {members.map((a) => (
                <div
                  key={a.id}
                  className="flex items-center justify-between gap-2 py-1"
                >
                  <div className="min-w-0 flex-1">
                    <span className="font-medium">{a.name}</span>
                    <span className="ml-2 text-xs text-neutral-500">
                      {a.platform}
                      {a.platform_uid && ` · ${a.platform_uid}`}
                      {" · "}#{a.id}
                      {a.artwork_count > 0 && ` · ${a.artwork_count} 件作品`}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    {mergeTarget && mergeTarget.id !== a.id && (
                      <button
                        onClick={() =>
                          handleLink(
                            mergeTarget.id,
                            a.canonical_id ?? a.id,
                          )
                        }
                        className="rounded bg-blue-600 px-2 py-0.5 text-xs text-white hover:bg-blue-700"
                      >
                        关联到此
                      </button>
                    )}
                    {!mergeTarget && (
                      <button
                        onClick={() =>
                          setMergeTarget({
                            id: a.id,
                            canonicalId: String(a.canonical_id ?? ""),
                          })
                        }
                        className="rounded border px-2 py-0.5 text-xs hover:bg-neutral-100 dark:border-neutral-600 dark:hover:bg-neutral-800"
                      >
                        关联
                      </button>
                    )}
                    {a.canonical_id && (
                      <button
                        onClick={() => handleUnlink(a.id)}
                        className="rounded border px-2 py-0.5 text-xs text-orange-600 hover:bg-orange-50 dark:border-neutral-600 dark:hover:bg-orange-950/30"
                      >
                        取消关联
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(a.id)}
                      className="rounded border px-2 py-0.5 text-xs text-red-600 hover:bg-red-50 dark:border-neutral-600 dark:hover:bg-red-950/30"
                    >
                      删除
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {mergeTarget && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white shadow-lg">
          选择要关联的目标作者（点击"关联到此"）
          <button
            onClick={() => setMergeTarget(null)}
            className="ml-3 underline"
          >
            取消
          </button>
        </div>
      )}
    </div>
  );
}
