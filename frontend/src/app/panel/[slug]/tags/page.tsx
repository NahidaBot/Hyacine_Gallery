"use client";

import { useCallback, useEffect, useState } from "react";
import type { Tag, TagType } from "@/types";
import {
  adminCreateTag,
  adminDeleteTag,
  adminFetchTags,
  adminFetchTagTypes,
  adminUpdateTag,
} from "@/lib/admin-api";

const COLOR_MAP: Record<string, string> = {
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

function TagTypeBadge({ type, tagTypes }: { type: string; tagTypes: TagType[] }) {
  const tt = tagTypes.find((t) => t.name === type);
  const color = tt?.color || "neutral";
  const cls = COLOR_MAP[color] || COLOR_MAP.neutral;
  return (
    <span className={`rounded px-2 py-0.5 text-xs ${cls}`}>
      {tt?.label || type}
    </span>
  );
}

export default function TagsPage() {
  const [tags, setTags] = useState<Tag[]>([]);
  const [tagTypes, setTagTypes] = useState<TagType[]>([]);
  const [loading, setLoading] = useState(true);

  // 创建
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("general");
  const [creating, setCreating] = useState(false);

  // 行内编辑
  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editType, setEditType] = useState("general");
  const [editAliasOfId, setEditAliasOfId] = useState<number | "">("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [tagsRes, typesRes] = await Promise.all([
        adminFetchTags(),
        adminFetchTagTypes(),
      ]);
      setTags(tagsRes.data);
      setTagTypes(typesRes);
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
    const name = newName.trim().replace(/^#/, "");
    if (!name) return;
    setCreating(true);
    try {
      await adminCreateTag({ name, type: newType });
      setNewName("");
      setNewType("general");
      await load();
    } catch (err) {
      alert(String(err));
    } finally {
      setCreating(false);
    }
  }

  function startEdit(tag: Tag) {
    setEditId(tag.id);
    setEditName(tag.name);
    setEditType(tag.type);
    setEditAliasOfId(tag.alias_of_id ?? "");
  }

  async function saveEdit() {
    if (editId === null) return;
    try {
      await adminUpdateTag(editId, {
        name: editName.trim(),
        type: editType,
        alias_of_id: editAliasOfId === "" ? null : Number(editAliasOfId),
      });
      setEditId(null);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`确认删除标签"${name}"？`)) return;
    try {
      await adminDeleteTag(id);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  // 按标签名查找
  const tagById = (id: number | null) => tags.find((t) => t.id === id);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">标签管理</h1>

      {/* 创建表单 */}
      <div className="mb-6 flex items-end gap-2">
        <div className="flex-1">
          <label className="mb-1 block text-sm font-medium">新标签</label>
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            placeholder="标签名称"
            className="w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">类型</label>
          <select
            value={newType}
            onChange={(e) => setNewType(e.target.value)}
            className="rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            {tagTypes.map((t) => (
              <option key={t.name} value={t.name}>
                {t.label || t.name}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {creating ? "..." : "添加"}
        </button>
      </div>

      {/* 标签列表 */}
      {loading ? (
        <p className="text-sm text-neutral-400">加载中...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-neutral-200 text-xs uppercase text-neutral-500 dark:border-neutral-700">
              <tr>
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">名称</th>
                <th className="px-3 py-2">类型</th>
                <th className="px-3 py-2">作品数</th>
                <th className="px-3 py-2">别名指向</th>
                <th className="px-3 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {tags.map((tag) => (
                <tr
                  key={tag.id}
                  className={`border-b border-neutral-100 dark:border-neutral-800 ${tag.alias_of_id ? "opacity-70" : ""}`}
                >
                  <td className="px-3 py-2 tabular-nums">{tag.id}</td>
                  <td className="px-3 py-2">
                    {editId === tag.id ? (
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && saveEdit()}
                        className="w-full rounded border border-blue-400 px-2 py-1 text-sm dark:bg-neutral-900"
                        autoFocus
                      />
                    ) : (
                      <span className={tag.alias_of_id ? "text-neutral-400 line-through" : ""}>
                        #{tag.name}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {editId === tag.id ? (
                      <select
                        value={editType}
                        onChange={(e) => setEditType(e.target.value)}
                        className="rounded border border-blue-400 px-2 py-1 text-sm dark:bg-neutral-900"
                      >
                        {tagTypes.map((t) => (
                          <option key={t.name} value={t.name}>
                            {t.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <TagTypeBadge type={tag.type} tagTypes={tagTypes} />
                    )}
                  </td>
                  <td className="px-3 py-2 tabular-nums">
                    {tag.artwork_count}
                  </td>
                  <td className="px-3 py-2">
                    {editId === tag.id ? (
                      <select
                        value={editAliasOfId}
                        onChange={(e) =>
                          setEditAliasOfId(e.target.value === "" ? "" : Number(e.target.value))
                        }
                        className="rounded border border-blue-400 px-2 py-1 text-sm dark:bg-neutral-900"
                      >
                        <option value="">— 无（独立标签）</option>
                        {tags
                          .filter((t) => t.id !== tag.id && !t.alias_of_id)
                          .map((t) => (
                            <option key={t.id} value={t.id}>
                              #{t.name}
                            </option>
                          ))}
                      </select>
                    ) : tag.alias_of_id ? (
                      <span className="text-xs text-amber-600 dark:text-amber-400">
                        → #{tagById(tag.alias_of_id)?.name ?? tag.alias_of_id}
                      </span>
                    ) : (
                      <span className="text-xs text-neutral-300 dark:text-neutral-600">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {editId === tag.id ? (
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
                          onClick={() => startEdit(tag)}
                          className="text-blue-600 hover:underline"
                        >
                          编辑
                        </button>
                        <button
                          onClick={() => handleDelete(tag.id, tag.name)}
                          className="text-red-500 hover:underline"
                        >
                          删除
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {tags.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-3 py-8 text-center text-neutral-400"
                  >
                    暂无标签。
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
