"use client";

import { useCallback, useEffect, useState } from "react";
import type { FriendLink } from "@/types";
import {
  adminCreateLink,
  adminDeleteLink,
  adminFetchLinks,
  adminUpdateLink,
} from "@/lib/admin-api";

type EditState = {
  name: string;
  url: string;
  description: string;
  avatar_url: string;
  sort_order: number;
  enabled: boolean;
};

const DEFAULT_EDIT: EditState = {
  name: "",
  url: "",
  description: "",
  avatar_url: "",
  sort_order: 100,
  enabled: true,
};

export default function LinksAdminPage() {
  const [links, setLinks] = useState<FriendLink[]>([]);
  const [loading, setLoading] = useState(true);

  // 新建表单
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [newLink, setNewLink] = useState<EditState>(DEFAULT_EDIT);

  // 行内编辑
  const [editId, setEditId] = useState<number | null>(null);
  const [editState, setEditState] = useState<EditState>(DEFAULT_EDIT);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setLinks(await adminFetchLinks());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleCreate() {
    if (!newLink.name.trim() || !newLink.url.trim()) return;
    setCreating(true);
    try {
      await adminCreateLink(newLink);
      setNewLink(DEFAULT_EDIT);
      setShowForm(false);
      await load();
    } catch (err) {
      alert(String(err));
    } finally {
      setCreating(false);
    }
  }

  function startEdit(link: FriendLink) {
    setEditId(link.id);
    setEditState({
      name: link.name,
      url: link.url,
      description: link.description,
      avatar_url: link.avatar_url,
      sort_order: link.sort_order,
      enabled: link.enabled,
    });
  }

  async function saveEdit() {
    if (editId === null) return;
    try {
      await adminUpdateLink(editId, editState);
      setEditId(null);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`确认删除友情链接"${name}"？`)) return;
    try {
      await adminDeleteLink(id);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">友情链接</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          + 添加
        </button>
      </div>

      {/* 新建表单 */}
      {showForm && (
        <div className="mb-6 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
          <h2 className="mb-3 text-sm font-semibold">新建友情链接</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-neutral-500">名称 *</label>
              <input
                type="text"
                value={newLink.name}
                onChange={(e) => setNewLink({ ...newLink, name: e.target.value })}
                placeholder="站点名称"
                className="w-full rounded border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-neutral-500">URL *</label>
              <input
                type="url"
                value={newLink.url}
                onChange={(e) => setNewLink({ ...newLink, url: e.target.value })}
                placeholder="https://example.com"
                className="w-full rounded border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-neutral-500">描述</label>
              <input
                type="text"
                value={newLink.description}
                onChange={(e) => setNewLink({ ...newLink, description: e.target.value })}
                placeholder="一句话简介"
                className="w-full rounded border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-neutral-500">头像 URL</label>
              <input
                type="url"
                value={newLink.avatar_url}
                onChange={(e) => setNewLink({ ...newLink, avatar_url: e.target.value })}
                placeholder="https://example.com/avatar.png"
                className="w-full rounded border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-neutral-500">排序（越小越靠前）</label>
              <input
                type="number"
                value={newLink.sort_order}
                onChange={(e) => setNewLink({ ...newLink, sort_order: Number(e.target.value) })}
                className="w-full rounded border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={newLink.enabled}
                  onChange={(e) => setNewLink({ ...newLink, enabled: e.target.checked })}
                  className="h-4 w-4"
                />
                启用
              </label>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleCreate}
              disabled={creating || !newLink.name.trim() || !newLink.url.trim()}
              className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? "..." : "保存"}
            </button>
            <button
              onClick={() => { setShowForm(false); setNewLink(DEFAULT_EDIT); }}
              className="rounded px-4 py-1.5 text-sm text-neutral-500 hover:text-neutral-800"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {/* 列表 */}
      {loading ? (
        <p className="text-sm text-neutral-400">加载中...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-neutral-200 text-xs uppercase text-neutral-500 dark:border-neutral-700">
              <tr>
                <th className="px-3 py-2">名称</th>
                <th className="px-3 py-2">URL</th>
                <th className="px-3 py-2">描述</th>
                <th className="px-3 py-2">排序</th>
                <th className="px-3 py-2">状态</th>
                <th className="px-3 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {links.map((link) =>
                editId === link.id ? (
                  <tr key={link.id} className="border-b border-neutral-100 bg-blue-50/30 dark:border-neutral-800 dark:bg-blue-900/10">
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        value={editState.name}
                        onChange={(e) => setEditState({ ...editState, name: e.target.value })}
                        className="w-full rounded border border-blue-400 px-2 py-1 text-sm dark:bg-neutral-900"
                        autoFocus
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="url"
                        value={editState.url}
                        onChange={(e) => setEditState({ ...editState, url: e.target.value })}
                        className="w-full rounded border border-blue-400 px-2 py-1 text-sm dark:bg-neutral-900"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        value={editState.description}
                        onChange={(e) => setEditState({ ...editState, description: e.target.value })}
                        className="w-full rounded border border-blue-400 px-2 py-1 text-sm dark:bg-neutral-900"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        value={editState.sort_order}
                        onChange={(e) => setEditState({ ...editState, sort_order: Number(e.target.value) })}
                        className="w-20 rounded border border-blue-400 px-2 py-1 text-sm dark:bg-neutral-900"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={editState.enabled}
                        onChange={(e) => setEditState({ ...editState, enabled: e.target.checked })}
                        className="h-4 w-4"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        <button onClick={saveEdit} className="text-blue-600 hover:underline">保存</button>
                        <button onClick={() => setEditId(null)} className="text-neutral-400 hover:underline">取消</button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={link.id} className="border-b border-neutral-100 dark:border-neutral-800">
                    <td className="px-3 py-2 font-medium">
                      <div className="flex items-center gap-2">
                        {link.avatar_url && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={link.avatar_url} alt="" className="h-6 w-6 rounded-full object-cover" />
                        )}
                        {link.name}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="max-w-[200px] truncate text-blue-600 hover:underline block"
                      >
                        {link.url}
                      </a>
                    </td>
                    <td className="px-3 py-2 text-neutral-500">{link.description || "—"}</td>
                    <td className="px-3 py-2 tabular-nums">{link.sort_order}</td>
                    <td className="px-3 py-2">
                      <span className={`rounded px-2 py-0.5 text-xs ${link.enabled ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : "bg-neutral-100 text-neutral-500 dark:bg-neutral-800"}`}>
                        {link.enabled ? "启用" : "禁用"}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        <button onClick={() => startEdit(link)} className="text-blue-600 hover:underline">编辑</button>
                        <button onClick={() => handleDelete(link.id, link.name)} className="text-red-500 hover:underline">删除</button>
                      </div>
                    </td>
                  </tr>
                )
              )}
              {links.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-neutral-400">
                    暂无友情链接，点击右上角添加。
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
