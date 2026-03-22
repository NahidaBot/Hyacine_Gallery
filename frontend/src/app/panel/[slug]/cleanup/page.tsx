"use client";

import { useCallback, useState } from "react";
import { getToken } from "@/lib/admin-api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      ...init?.headers,
    },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

interface DuplicatePair {
  tag_a: { id: number; name: string; type: string };
  tag_b: { id: number; name: string; type: string };
  similarity: number;
}

interface OrphanImage {
  id: number;
  artwork_id: number;
  page_index: number;
  storage_path: string;
}

export default function CleanupPage() {
  const [threshold, setThreshold] = useState(0.8);
  const [duplicates, setDuplicates] = useState<DuplicatePair[]>([]);
  const [orphans, setOrphans] = useState<OrphanImage[]>([]);
  const [loading, setLoading] = useState({ duplicates: false, orphans: false });

  const loadDuplicates = useCallback(async () => {
    setLoading((l) => ({ ...l, duplicates: true }));
    try {
      const data = await apiFetch<DuplicatePair[]>(
        `/api/admin/tags/duplicates?threshold=${threshold}`,
      );
      setDuplicates(data);
    } finally {
      setLoading((l) => ({ ...l, duplicates: false }));
    }
  }, [threshold]);

  const loadOrphans = useCallback(async () => {
    setLoading((l) => ({ ...l, orphans: true }));
    try {
      const data = await apiFetch<OrphanImage[]>(
        "/api/admin/cleanup/orphan-images",
      );
      setOrphans(data);
    } finally {
      setLoading((l) => ({ ...l, orphans: false }));
    }
  }, []);

  async function handleMerge(keepId: number, mergeId: number) {
    await apiFetch("/api/admin/tags/merge", {
      method: "POST",
      body: JSON.stringify({ keep_id: keepId, merge_id: mergeId }),
    });
    setDuplicates((d) =>
      d.filter(
        (p) =>
          !(p.tag_a.id === mergeId || p.tag_b.id === mergeId),
      ),
    );
  }

  async function handleCleanOrphans() {
    const result = await apiFetch<{ cleaned: number }>(
      "/api/admin/cleanup/orphan-images",
      { method: "POST" },
    );
    alert(`已清理 ${result.cleaned} 条记录`);
    setOrphans([]);
  }

  return (
    <div>
      <h1 className="mb-6 text-xl font-bold">数据清理</h1>

      {/* 重复标签 */}
      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">重复标签检测</h2>
        <div className="mb-3 flex items-center gap-3">
          <label className="text-sm">
            相似度阈值:
            <input
              type="number"
              min={0.5}
              max={1}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="ml-2 w-20 rounded border px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            />
          </label>
          <button
            onClick={loadDuplicates}
            disabled={loading.duplicates}
            className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading.duplicates ? "检测中..." : "检测"}
          </button>
        </div>
        {duplicates.length > 0 && (
          <div className="space-y-2">
            {duplicates.map((d, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded border p-2 dark:border-neutral-700"
              >
                <div className="text-sm">
                  <strong>{d.tag_a.name}</strong>
                  <span className="mx-2 text-neutral-400">~</span>
                  <strong>{d.tag_b.name}</strong>
                  <span className="ml-2 text-xs text-neutral-500">
                    ({(d.similarity * 100).toFixed(0)}%)
                  </span>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => handleMerge(d.tag_a.id, d.tag_b.id)}
                    className="rounded bg-green-600 px-2 py-0.5 text-xs text-white hover:bg-green-700"
                  >
                    保留 {d.tag_a.name}
                  </button>
                  <button
                    onClick={() => handleMerge(d.tag_b.id, d.tag_a.id)}
                    className="rounded bg-green-600 px-2 py-0.5 text-xs text-white hover:bg-green-700"
                  >
                    保留 {d.tag_b.name}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        {duplicates.length === 0 && !loading.duplicates && (
          <p className="text-sm text-neutral-500">点击"检测"开始扫描</p>
        )}
      </section>

      {/* 悬空图片 */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">悬空图片清理</h2>
        <div className="mb-3 flex items-center gap-3">
          <button
            onClick={loadOrphans}
            disabled={loading.orphans}
            className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading.orphans ? "扫描中..." : "扫描"}
          </button>
          {orphans.length > 0 && (
            <button
              onClick={handleCleanOrphans}
              className="rounded bg-red-600 px-4 py-1.5 text-sm text-white hover:bg-red-700"
            >
              清理 {orphans.length} 条
            </button>
          )}
        </div>
        {orphans.length > 0 && (
          <div className="max-h-64 overflow-y-auto rounded border p-2 text-xs dark:border-neutral-700">
            {orphans.map((o) => (
              <div key={o.id} className="py-0.5">
                作品 #{o.artwork_id} 第 {o.page_index} 页 — {o.storage_path}
              </div>
            ))}
          </div>
        )}
        {orphans.length === 0 && !loading.orphans && (
          <p className="text-sm text-neutral-500">点击"扫描"检查悬空记录</p>
        )}
      </section>
    </div>
  );
}
