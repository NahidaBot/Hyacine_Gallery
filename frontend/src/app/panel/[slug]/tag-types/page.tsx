"use client";

import { useCallback, useEffect, useState } from "react";
import type { TagType } from "@/types";
import {
  adminFetchTagTypes,
  adminCreateTagType,
  adminUpdateTagType,
  adminDeleteTagType,
} from "@/lib/admin-api";

const PRESET_COLORS = [
  "neutral",
  "red",
  "orange",
  "yellow",
  "green",
  "teal",
  "blue",
  "indigo",
  "purple",
  "pink",
];

function ColorBadge({ color }: { color: string }) {
  const colorMap: Record<string, string> = {
    neutral: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400",
    red: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    orange: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    yellow: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    green: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    teal: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
    blue: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    indigo: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
    purple: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
    pink: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400",
  };
  const cls = colorMap[color] || colorMap.neutral;
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs ${cls}`}>
      {color}
    </span>
  );
}

export default function TagTypesPage() {
  const [types, setTypes] = useState<TagType[]>([]);
  const [loading, setLoading] = useState(true);

  // 创建表单
  const [newName, setNewName] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [newColor, setNewColor] = useState("neutral");
  const [newOrder, setNewOrder] = useState(0);
  const [creating, setCreating] = useState(false);

  // 行内编辑
  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editLabel, setEditLabel] = useState("");
  const [editColor, setEditColor] = useState("neutral");
  const [editOrder, setEditOrder] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTypes(await adminFetchTagTypes());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate() {
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    try {
      await adminCreateTagType({
        name,
        label: newLabel.trim() || name,
        color: newColor,
        sort_order: newOrder,
      });
      setNewName("");
      setNewLabel("");
      setNewColor("neutral");
      setNewOrder(0);
      await load();
    } catch (err) {
      alert(String(err));
    } finally {
      setCreating(false);
    }
  }

  function startEdit(tt: TagType) {
    setEditId(tt.id);
    setEditName(tt.name);
    setEditLabel(tt.label);
    setEditColor(tt.color);
    setEditOrder(tt.sort_order);
  }

  async function saveEdit() {
    if (editId === null) return;
    try {
      await adminUpdateTagType(editId, {
        name: editName.trim(),
        label: editLabel.trim(),
        color: editColor,
        sort_order: editOrder,
      });
      setEditId(null);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`确认删除标签类型"${name}"？使用此类型的标签将变为无效。`))
      return;
    try {
      await adminDeleteTagType(id);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  const inputCls =
    "rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900";
  const editInputCls =
    "rounded border border-blue-400 px-2 py-1 text-sm dark:bg-neutral-900";

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold">标签类型</h1>
      <p className="mb-6 text-sm text-neutral-400">
        管理用于分类标签的类别。
      </p>

      {/* 创建表单 */}
      <div className="mb-6 rounded border border-neutral-200 p-4 dark:border-neutral-800">
        <h3 className="mb-3 text-sm font-semibold">添加标签类型</h3>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs text-neutral-500">名称（键）</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="例如 costume"
              className={`w-36 ${inputCls}`}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-500">显示名</label>
            <input
              type="text"
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              placeholder="例如 服装"
              className={`w-36 ${inputCls}`}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-500">颜色</label>
            <select
              value={newColor}
              onChange={(e) => setNewColor(e.target.value)}
              className={inputCls}
            >
              {PRESET_COLORS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-500">排序</label>
            <input
              type="number"
              value={newOrder}
              onChange={(e) => setNewOrder(Number(e.target.value))}
              className={`w-20 ${inputCls}`}
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={creating}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {creating ? "..." : "添加"}
          </button>
        </div>
      </div>

      {/* 列表 */}
      {loading ? (
        <p className="text-sm text-neutral-400">加载中...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-neutral-200 text-xs uppercase text-neutral-500 dark:border-neutral-700">
              <tr>
                <th className="px-3 py-2">排序</th>
                <th className="px-3 py-2">名称</th>
                <th className="px-3 py-2">显示名</th>
                <th className="px-3 py-2">颜色</th>
                <th className="px-3 py-2">标签数</th>
                <th className="px-3 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {types.map((tt) => (
                <tr
                  key={tt.id}
                  className="border-b border-neutral-100 dark:border-neutral-800"
                >
                  <td className="px-3 py-2 tabular-nums">
                    {editId === tt.id ? (
                      <input
                        type="number"
                        value={editOrder}
                        onChange={(e) => setEditOrder(Number(e.target.value))}
                        className={`w-16 ${editInputCls}`}
                      />
                    ) : (
                      tt.sort_order
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {editId === tt.id ? (
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className={`w-32 ${editInputCls}`}
                        autoFocus
                      />
                    ) : (
                      <code className="text-xs">{tt.name}</code>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {editId === tt.id ? (
                      <input
                        type="text"
                        value={editLabel}
                        onChange={(e) => setEditLabel(e.target.value)}
                        className={`w-32 ${editInputCls}`}
                      />
                    ) : (
                      tt.label
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {editId === tt.id ? (
                      <select
                        value={editColor}
                        onChange={(e) => setEditColor(e.target.value)}
                        className={editInputCls}
                      >
                        {PRESET_COLORS.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <ColorBadge color={tt.color} />
                    )}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{tt.tag_count}</td>
                  <td className="px-3 py-2">
                    {editId === tt.id ? (
                      <div className="flex gap-2">
                        <button
                          onClick={saveEdit}
                          className="text-blue-600 hover:underline"
                        >
                          保存
                        </button>
                        <button
                          onClick={() => setEditId(null)}
                          className="text-neutral-400 hover:underline"
                        >
                          取消
                        </button>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button
                          onClick={() => startEdit(tt)}
                          className="text-blue-600 hover:underline"
                        >
                          编辑
                        </button>
                        <button
                          onClick={() => handleDelete(tt.id, tt.name)}
                          className="text-red-500 hover:underline"
                        >
                          删除
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {types.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-3 py-8 text-center text-neutral-400"
                  >
                    暂无标签类型。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
