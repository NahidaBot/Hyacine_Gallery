"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { adminFetchPostLogs } from "@/lib/admin-api";
import type { BotPostLog } from "@/types";

export default function PostLogsPage() {
  const { slug } = useParams<{ slug: string }>();
  const [logs, setLogs] = useState<BotPostLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const pageSize = 20;

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await adminFetchPostLogs({ page, page_size: pageSize });
      setLogs(data.data);
      setTotal(data.total);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">发布记录</h1>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {loading ? (
        <p className="text-neutral-500">加载中...</p>
      ) : (
        <>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 text-left dark:border-neutral-700">
                <th className="pb-2">ID</th>
                <th className="pb-2">作品</th>
                <th className="pb-2">频道</th>
                <th className="pb-2">消息</th>
                <th className="pb-2">发布者</th>
                <th className="pb-2">发布时间</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr
                  key={log.id}
                  className="border-b border-neutral-100 dark:border-neutral-800"
                >
                  <td className="py-2 pr-2">{log.id}</td>
                  <td className="py-2 pr-2">
                    <Link
                      href={`/panel/${slug}/artworks/${log.artwork_id}`}
                      className="text-blue-600 hover:underline"
                    >
                      #{log.artwork_id}
                    </Link>
                  </td>
                  <td className="py-2 pr-2 font-mono text-xs">
                    {log.channel_id}
                  </td>
                  <td className="py-2 pr-2">
                    {log.message_link ? (
                      <a
                        href={log.message_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        {log.message_id || "链接"}
                      </a>
                    ) : (
                      <span className="text-neutral-400">
                        {log.message_id || "—"}
                      </span>
                    )}
                  </td>
                  <td className="py-2 pr-2">{log.posted_by || "—"}</td>
                  <td className="py-2 pr-2 text-neutral-500">
                    {new Date(log.posted_at).toLocaleString()}
                  </td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="py-4 text-center text-neutral-400"
                  >
                    暂无发布记录。
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center gap-4 text-sm">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded border px-3 py-1 disabled:opacity-30 dark:border-neutral-700"
              >
                上一页
              </button>
              <span className="text-neutral-500">
                第 {page} / {totalPages} 页（共 {total} 条）
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="rounded border px-3 py-1 disabled:opacity-30 dark:border-neutral-700"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
