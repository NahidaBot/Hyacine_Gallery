"use client";

import { useCallback, useEffect, useState } from "react";
import {
  adminFetchBotChannels,
  adminCreateBotChannel,
  adminUpdateBotChannel,
  adminDeleteBotChannel,
} from "@/lib/admin-api";
import type { BotChannel } from "@/types";

const CONDITION_FIELDS = [
  { key: "is_ai", label: "AI 作品", type: "bool" as const },
  { key: "is_nsfw", label: "NSFW 作品", type: "bool" as const },
  { key: "platform", label: "平台等于", type: "text" as const },
  { key: "tags_any", label: "包含任一标签（逗号分隔）", type: "tags" as const },
];

export default function BotChannelsPage() {
  const [channels, setChannels] = useState<BotChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 创建表单
  const [newChannelId, setNewChannelId] = useState("");
  const [newName, setNewName] = useState("");
  const [newIsDefault, setNewIsDefault] = useState(false);
  const [newPriority, setNewPriority] = useState(0);
  const [newConditions, setNewConditions] = useState<Record<string, unknown>>({});

  // 编辑状态
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editData, setEditData] = useState<{
    channel_id: string;
    name: string;
    is_default: boolean;
    priority: number;
    conditions: Record<string, unknown>;
    enabled: boolean;
  }>({
    channel_id: "",
    name: "",
    is_default: false,
    priority: 0,
    conditions: {},
    enabled: true,
  });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await adminFetchBotChannels();
      setChannels(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async () => {
    if (!newChannelId.trim()) return;
    try {
      await adminCreateBotChannel({
        channel_id: newChannelId.trim(),
        name: newName.trim(),
        is_default: newIsDefault,
        priority: newPriority,
        conditions: newConditions,
      });
      setNewChannelId("");
      setNewName("");
      setNewIsDefault(false);
      setNewPriority(0);
      setNewConditions({});
      await load();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确认删除此频道？")) return;
    try {
      await adminDeleteBotChannel(id);
      await load();
    } catch (e) {
      setError(String(e));
    }
  };

  const startEdit = (ch: BotChannel) => {
    setEditingId(ch.id);
    setEditData({
      channel_id: ch.channel_id,
      name: ch.name,
      is_default: ch.is_default,
      priority: ch.priority,
      conditions: ch.conditions ?? {},
      enabled: ch.enabled,
    });
  };

  const handleSaveEdit = async () => {
    if (editingId === null) return;
    try {
      await adminUpdateBotChannel(editingId, editData);
      setEditingId(null);
      await load();
    } catch (e) {
      setError(String(e));
    }
  };

  if (loading) return <p className="text-neutral-500">加载中...</p>;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Bot 频道</h1>
      <p className="mb-4 text-sm text-neutral-500">
        配置频道路由规则。按优先级评估（数值越小优先级越高），第一个匹配的条件生效；默认频道作为兜底。
      </p>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {/* 创建表单 */}
      <div className="mb-6 rounded border border-neutral-200 p-4 dark:border-neutral-700">
        <h2 className="mb-3 text-sm font-semibold">添加频道</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-neutral-500">频道 ID</label>
            <input
              type="text"
              value={newChannelId}
              onChange={(e) => setNewChannelId(e.target.value)}
              placeholder="@channel or -100xxx"
              className="w-full rounded border border-neutral-300 px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            />
          </div>
          <div>
            <label className="block text-xs text-neutral-500">名称</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="显示名称"
              className="w-full rounded border border-neutral-300 px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            />
          </div>
          <div>
            <label className="block text-xs text-neutral-500">优先级</label>
            <input
              type="number"
              value={newPriority}
              onChange={(e) => setNewPriority(Number(e.target.value))}
              className="w-full rounded border border-neutral-300 px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            />
          </div>
          <div className="flex items-end gap-3">
            <label className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={newIsDefault}
                onChange={(e) => setNewIsDefault(e.target.checked)}
              />
              默认频道
            </label>
          </div>
        </div>
        <ConditionEditor
          value={newConditions}
          onChange={setNewConditions}
          className="mt-3"
        />
        <button
          onClick={handleCreate}
          className="mt-3 rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
        >
          添加
        </button>
      </div>

      {/* 频道列表 */}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-200 text-left dark:border-neutral-700">
            <th className="pb-2">优先级</th>
            <th className="pb-2">频道</th>
            <th className="pb-2">名称</th>
            <th className="pb-2">条件</th>
            <th className="pb-2">默认</th>
            <th className="pb-2">启用</th>
            <th className="pb-2">操作</th>
          </tr>
        </thead>
        <tbody>
          {channels.map((ch) =>
            editingId === ch.id ? (
              <tr key={ch.id} className="border-b border-neutral-100 dark:border-neutral-800">
                <td className="py-2 pr-2">
                  <input
                    type="number"
                    value={editData.priority}
                    onChange={(e) =>
                      setEditData((d) => ({ ...d, priority: Number(e.target.value) }))
                    }
                    className="w-16 rounded border px-1 py-0.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
                  />
                </td>
                <td className="py-2 pr-2">
                  <input
                    type="text"
                    value={editData.channel_id}
                    onChange={(e) =>
                      setEditData((d) => ({ ...d, channel_id: e.target.value }))
                    }
                    className="w-40 rounded border px-1 py-0.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
                  />
                </td>
                <td className="py-2 pr-2">
                  <input
                    type="text"
                    value={editData.name}
                    onChange={(e) =>
                      setEditData((d) => ({ ...d, name: e.target.value }))
                    }
                    className="w-32 rounded border px-1 py-0.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
                  />
                </td>
                <td className="py-2 pr-2">
                  <ConditionEditor
                    value={editData.conditions}
                    onChange={(c) => setEditData((d) => ({ ...d, conditions: c }))}
                  />
                </td>
                <td className="py-2 pr-2">
                  <input
                    type="checkbox"
                    checked={editData.is_default}
                    onChange={(e) =>
                      setEditData((d) => ({ ...d, is_default: e.target.checked }))
                    }
                  />
                </td>
                <td className="py-2 pr-2">
                  <input
                    type="checkbox"
                    checked={editData.enabled}
                    onChange={(e) =>
                      setEditData((d) => ({ ...d, enabled: e.target.checked }))
                    }
                  />
                </td>
                <td className="py-2 space-x-2">
                  <button onClick={handleSaveEdit} className="text-blue-600 hover:underline">
                    保存
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="text-neutral-500 hover:underline"
                  >
                    取消
                  </button>
                </td>
              </tr>
            ) : (
              <tr key={ch.id} className="border-b border-neutral-100 dark:border-neutral-800">
                <td className="py-2 pr-2">{ch.priority}</td>
                <td className="py-2 pr-2 font-mono text-xs">{ch.channel_id}</td>
                <td className="py-2 pr-2">{ch.name || "—"}</td>
                <td className="py-2 pr-2">
                  <ConditionBadges conditions={ch.conditions} />
                </td>
                <td className="py-2 pr-2">
                  {ch.is_default && (
                    <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-800 dark:bg-green-900 dark:text-green-200">
                      默认
                    </span>
                  )}
                </td>
                <td className="py-2 pr-2">
                  {ch.enabled ? (
                    <span className="text-green-600">开</span>
                  ) : (
                    <span className="text-neutral-400">关</span>
                  )}
                </td>
                <td className="py-2 space-x-2">
                  <button onClick={() => startEdit(ch)} className="text-blue-600 hover:underline">
                    编辑
                  </button>
                  <button
                    onClick={() => handleDelete(ch.id)}
                    className="text-red-600 hover:underline"
                  >
                    删除
                  </button>
                </td>
              </tr>
            ),
          )}
          {channels.length === 0 && (
            <tr>
              <td colSpan={7} className="py-4 text-center text-neutral-400">
                暂无频道配置，请在上方添加。
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── 条件编辑器 ──

function ConditionEditor({
  value,
  onChange,
  className = "",
}: {
  value: Record<string, unknown>;
  onChange: (v: Record<string, unknown>) => void;
  className?: string;
}) {
  const updateField = (key: string, val: unknown) => {
    if (val === "" || val === null || val === undefined) {
      const next = { ...value };
      delete next[key];
      onChange(next);
    } else {
      onChange({ ...value, [key]: val });
    }
  };

  return (
    <div className={`space-y-1.5 ${className}`}>
      <p className="text-xs font-medium text-neutral-500">
        条件（留空 = 匹配所有）
      </p>
      {CONDITION_FIELDS.map((f) => (
        <div key={f.key} className="flex items-center gap-2 text-xs">
          <span className="w-40 shrink-0">{f.label}</span>
          {f.type === "bool" ? (
            <select
              value={
                value[f.key] === true
                  ? "true"
                  : value[f.key] === false
                    ? "false"
                    : ""
              }
              onChange={(e) => {
                const v = e.target.value;
                updateField(f.key, v === "" ? undefined : v === "true");
              }}
              className="rounded border px-1 py-0.5 dark:border-neutral-700 dark:bg-neutral-900"
            >
              <option value="">—</option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          ) : f.type === "tags" ? (
            <input
              type="text"
              value={
                Array.isArray(value[f.key])
                  ? (value[f.key] as string[]).join(", ")
                  : ""
              }
              onChange={(e) => {
                const raw = e.target.value;
                if (!raw.trim()) {
                  updateField(f.key, undefined);
                } else {
                  updateField(
                    f.key,
                    raw.split(/[,\s]+/).filter(Boolean),
                  );
                }
              }}
              placeholder="tag1, tag2"
              className="flex-1 rounded border px-1 py-0.5 dark:border-neutral-700 dark:bg-neutral-900"
            />
          ) : (
            <input
              type="text"
              value={(value[f.key] as string) ?? ""}
              onChange={(e) => updateField(f.key, e.target.value || undefined)}
              className="flex-1 rounded border px-1 py-0.5 dark:border-neutral-700 dark:bg-neutral-900"
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ── 条件展示 ──

function ConditionBadges({
  conditions,
}: {
  conditions: Record<string, unknown>;
}) {
  const entries = Object.entries(conditions ?? {});
  if (entries.length === 0) {
    return <span className="text-xs text-neutral-400">匹配所有</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {entries.map(([k, v]) => (
        <span
          key={k}
          className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs dark:bg-neutral-800"
        >
          {k}={JSON.stringify(v)}
        </span>
      ))}
    </div>
  );
}
