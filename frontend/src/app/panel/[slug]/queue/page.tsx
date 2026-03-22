"use client";

import { useCallback, useEffect, useState } from "react";
import {
  deleteQueueItem,
  fetchBotSettings,
  fetchNextTimes,
  fetchQueue,
  saveBotSettings,
  updateQueuePriority,
  type NextTimesResponse,
  type QueueItem,
} from "@/lib/queue-api";

type Tab = "pending" | "done" | "failed";

const QUEUE_SETTING_KEYS = [
  {
    key: "queue_enabled",
    label: "启用定时队列",
    type: "checkbox" as const,
    default: "true",
    description: "关闭后 bot 不再自动从队列发布",
  },
  {
    key: "queue_interval_minutes",
    label: "发布间隔（分钟）",
    type: "number" as const,
    default: "120",
    description: "每隔多少分钟从队列发一条",
  },
  {
    key: "queue_daily_limit",
    label: "每日上限",
    type: "number" as const,
    default: "10",
    description: "每日最多发布条数（0 = 不限）",
  },
];

export default function QueuePage() {
  const [tab, setTab] = useState<Tab>("pending");
  const [items, setItems] = useState<QueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 配置
  const [settingValues, setSettingValues] = useState<Record<string, string>>({});
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsSaved, setSettingsSaved] = useState(false);

  // 下次发布预测
  const [nextTimes, setNextTimes] = useState<NextTimesResponse | null>(null);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchQueue(tab);
      setItems(data.data);
      setTotal(data.total);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [tab]);

  const loadSettings = useCallback(async () => {
    try {
      const data = await fetchBotSettings();
      const map: Record<string, string> = {};
      for (const s of data) map[s.key] = s.value;
      for (const k of QUEUE_SETTING_KEYS) {
        if (!(k.key in map)) map[k.key] = k.default;
      }
      setSettingValues(map);
    } catch (_e) {
      // 静默失败，不影响队列展示
    }
  }, []);

  const loadNextTimes = useCallback(async () => {
    try {
      const data = await fetchNextTimes(5);
      setNextTimes(data);
    } catch (_e) {
      // 静默失败
    }
  }, []);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  useEffect(() => {
    loadSettings();
    loadNextTimes();
  }, [loadSettings, loadNextTimes]);

  async function handleDelete(id: number) {
    if (!confirm("从队列移除该条目？")) return;
    try {
      await deleteQueueItem(id);
      await loadQueue();
      await loadNextTimes();
    } catch (e) {
      alert(String(e));
    }
  }

  async function handleMoveUp(item: QueueItem, index: number) {
    if (index === 0) return;
    const prev = items[index - 1];
    try {
      await updateQueuePriority(item.id, prev.priority - 1);
      await loadQueue();
    } catch (e) {
      alert(String(e));
    }
  }

  async function handleMoveDown(item: QueueItem, index: number) {
    if (index === items.length - 1) return;
    const next = items[index + 1];
    try {
      await updateQueuePriority(item.id, next.priority + 1);
      await loadQueue();
    } catch (e) {
      alert(String(e));
    }
  }

  async function handleSaveSettings() {
    setSavingSettings(true);
    setSettingsSaved(false);
    try {
      await saveBotSettings(settingValues);
      setSettingsSaved(true);
      await loadNextTimes();
      setTimeout(() => setSettingsSaved(false), 2000);
    } catch (e) {
      alert(String(e));
    } finally {
      setSavingSettings(false);
    }
  }

  function formatTime(iso: string) {
    return new Date(iso).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <div className="max-w-4xl">
      <h1 className="mb-6 text-2xl font-bold">发布队列</h1>

      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        {/* 队列配置 */}
        <div className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-700">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-neutral-500">
            队列配置
          </h2>
          <div className="space-y-4">
            {QUEUE_SETTING_KEYS.map((k) => (
              <div key={k.key}>
                <label className="flex items-center justify-between text-sm font-medium">
                  {k.label}
                </label>
                <p className="mb-1 text-xs text-neutral-500">{k.description}</p>
                {k.type === "checkbox" ? (
                  <input
                    type="checkbox"
                    checked={settingValues[k.key] !== "false"}
                    onChange={(e) =>
                      setSettingValues((v) => ({
                        ...v,
                        [k.key]: e.target.checked ? "true" : "false",
                      }))
                    }
                    className="h-4 w-4 accent-blue-600"
                  />
                ) : (
                  <input
                    type="number"
                    value={settingValues[k.key] ?? k.default}
                    onChange={(e) =>
                      setSettingValues((v) => ({ ...v, [k.key]: e.target.value }))
                    }
                    className="w-full rounded border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
                  />
                )}
              </div>
            ))}
          </div>
          <button
            onClick={handleSaveSettings}
            disabled={savingSettings}
            className="mt-4 rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {savingSettings ? "保存中..." : settingsSaved ? "已保存 ✓" : "保存配置"}
          </button>
        </div>

        {/* 预计发布时间 */}
        <div className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-700">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-neutral-500">
            预计发布时间
          </h2>
          {nextTimes ? (
            nextTimes.pending_count === 0 ? (
              <p className="text-sm text-neutral-400">队列为空</p>
            ) : (
              <>
                <p className="mb-3 text-xs text-neutral-500">
                  间隔 {nextTimes.interval_minutes} 分钟 · 待发 {nextTimes.pending_count} 条
                </p>
                <ol className="space-y-1">
                  {nextTimes.times.map((t, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      <span className="w-5 text-xs text-neutral-400">#{i + 1}</span>
                      <span>{formatTime(t)}</span>
                    </li>
                  ))}
                </ol>
              </>
            )
          ) : (
            <p className="text-sm text-neutral-400">加载中...</p>
          )}
        </div>
      </div>

      {/* 标签页 */}
      <div className="mb-4 flex gap-2 border-b border-neutral-200 dark:border-neutral-700">
        {(["pending", "done", "failed"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              tab === t
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
            }`}
          >
            {t === "pending" ? "待发布" : t === "done" ? "已完成" : "失败"}
          </button>
        ))}
        <span className="ml-auto self-center text-xs text-neutral-400">
          共 {total} 条
        </span>
      </div>

      {error && <p className="mb-4 text-sm text-red-500">{error}</p>}

      {loading ? (
        <p className="text-sm text-neutral-400">加载中...</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-neutral-400">
          {tab === "pending" ? "队列为空" : "暂无记录"}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-neutral-200 text-xs uppercase text-neutral-500 dark:border-neutral-700">
              <tr>
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">作品 ID</th>
                <th className="px-3 py-2">优先级</th>
                <th className="px-3 py-2">添加人</th>
                <th className="px-3 py-2">入队时间</th>
                {tab !== "pending" && (
                  <th className="px-3 py-2">处理时间</th>
                )}
                {tab === "failed" && (
                  <th className="px-3 py-2">错误</th>
                )}
                {tab === "pending" && (
                  <th className="px-3 py-2">操作</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {items.map((item, index) => (
                <tr key={item.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
                  <td className="px-3 py-2 text-neutral-400">#{item.id}</td>
                  <td className="px-3 py-2">
                    <a
                      href={`../artworks/${item.artwork_id}`}
                      className="text-blue-600 hover:underline"
                    >
                      #{item.artwork_id}
                    </a>
                  </td>
                  <td className="px-3 py-2 tabular-nums">{item.priority}</td>
                  <td className="px-3 py-2 text-neutral-500">{item.added_by || "—"}</td>
                  <td className="px-3 py-2 text-neutral-500 tabular-nums">
                    {formatTime(item.created_at)}
                  </td>
                  {tab !== "pending" && (
                    <td className="px-3 py-2 text-neutral-500 tabular-nums">
                      {item.processed_at ? formatTime(item.processed_at) : "—"}
                    </td>
                  )}
                  {tab === "failed" && (
                    <td className="max-w-xs truncate px-3 py-2 text-xs text-red-500">
                      {item.error || "—"}
                    </td>
                  )}
                  {tab === "pending" && (
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleMoveUp(item, index)}
                          disabled={index === 0}
                          title="上移（提高优先级）"
                          className="rounded px-1.5 py-0.5 text-xs hover:bg-neutral-100 disabled:opacity-30 dark:hover:bg-neutral-700"
                        >
                          ↑
                        </button>
                        <button
                          onClick={() => handleMoveDown(item, index)}
                          disabled={index === items.length - 1}
                          title="下移（降低优先级）"
                          className="rounded px-1.5 py-0.5 text-xs hover:bg-neutral-100 disabled:opacity-30 dark:hover:bg-neutral-700"
                        >
                          ↓
                        </button>
                        <button
                          onClick={() => handleDelete(item.id)}
                          className="ml-1 rounded px-1.5 py-0.5 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                        >
                          移除
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
