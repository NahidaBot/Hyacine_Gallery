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
  { key: "is_ai", label: "AI artwork", type: "bool" as const },
  { key: "is_nsfw", label: "NSFW artwork", type: "bool" as const },
  { key: "platform", label: "Platform equals", type: "text" as const },
  { key: "tags_any", label: "Has any tag (comma-separated)", type: "tags" as const },
];

export default function BotChannelsPage() {
  const [channels, setChannels] = useState<BotChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Create form
  const [newChannelId, setNewChannelId] = useState("");
  const [newName, setNewName] = useState("");
  const [newIsDefault, setNewIsDefault] = useState(false);
  const [newPriority, setNewPriority] = useState(0);
  const [newConditions, setNewConditions] = useState<Record<string, unknown>>({});

  // Edit state
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
    if (!confirm("Delete this channel?")) return;
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

  if (loading) return <p className="text-neutral-500">Loading...</p>;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Bot Channels</h1>
      <p className="mb-4 text-sm text-neutral-500">
        Configure channel routing rules. Channels are evaluated by priority (lower = higher priority). First matching condition wins; default channel is used as fallback.
      </p>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {/* Create form */}
      <div className="mb-6 rounded border border-neutral-200 p-4 dark:border-neutral-700">
        <h2 className="mb-3 text-sm font-semibold">Add Channel</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-neutral-500">Channel ID</label>
            <input
              type="text"
              value={newChannelId}
              onChange={(e) => setNewChannelId(e.target.value)}
              placeholder="@channel or -100xxx"
              className="w-full rounded border border-neutral-300 px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            />
          </div>
          <div>
            <label className="block text-xs text-neutral-500">Name</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Display name"
              className="w-full rounded border border-neutral-300 px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            />
          </div>
          <div>
            <label className="block text-xs text-neutral-500">Priority</label>
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
              Default channel
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
          Add
        </button>
      </div>

      {/* Channel list */}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-200 text-left dark:border-neutral-700">
            <th className="pb-2">Priority</th>
            <th className="pb-2">Channel</th>
            <th className="pb-2">Name</th>
            <th className="pb-2">Conditions</th>
            <th className="pb-2">Default</th>
            <th className="pb-2">Enabled</th>
            <th className="pb-2">Actions</th>
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
                    Save
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="text-neutral-500 hover:underline"
                  >
                    Cancel
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
                      default
                    </span>
                  )}
                </td>
                <td className="py-2 pr-2">
                  {ch.enabled ? (
                    <span className="text-green-600">on</span>
                  ) : (
                    <span className="text-neutral-400">off</span>
                  )}
                </td>
                <td className="py-2 space-x-2">
                  <button onClick={() => startEdit(ch)} className="text-blue-600 hover:underline">
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(ch.id)}
                    className="text-red-600 hover:underline"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ),
          )}
          {channels.length === 0 && (
            <tr>
              <td colSpan={7} className="py-4 text-center text-neutral-400">
                No channels configured. Add one above.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── Condition Editor ──

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
        Conditions (empty = match all)
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

// ── Condition display ──

function ConditionBadges({
  conditions,
}: {
  conditions: Record<string, unknown>;
}) {
  const entries = Object.entries(conditions ?? {});
  if (entries.length === 0) {
    return <span className="text-xs text-neutral-400">match all</span>;
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
