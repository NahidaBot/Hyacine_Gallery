"use client";

import { useCallback, useEffect, useState } from "react";
import type { Tag } from "@/types";
import {
  adminCreateTag,
  adminDeleteTag,
  adminFetchTags,
  adminUpdateTag,
} from "@/lib/admin-api";

const TAG_TYPES = ["general", "character", "artist", "meta"];

export default function TagsPage() {
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);

  // Create
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("general");
  const [creating, setCreating] = useState(false);

  // Inline edit
  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editType, setEditType] = useState("general");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminFetchTags();
      setTags(data.data);
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
  }

  async function saveEdit() {
    if (editId === null) return;
    try {
      await adminUpdateTag(editId, { name: editName.trim(), type: editType });
      setEditId(null);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Delete tag "${name}"?`)) return;
    try {
      await adminDeleteTag(id);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Tags</h1>

      {/* Create form */}
      <div className="mb-6 flex items-end gap-2">
        <div className="flex-1">
          <label className="mb-1 block text-sm font-medium">New Tag</label>
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            placeholder="tag name"
            className="w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Type</label>
          <select
            value={newType}
            onChange={(e) => setNewType(e.target.value)}
            className="rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            {TAG_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {creating ? "..." : "Add"}
        </button>
      </div>

      {/* Tag list */}
      {loading ? (
        <p className="text-sm text-neutral-400">Loading...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-neutral-200 text-xs uppercase text-neutral-500 dark:border-neutral-700">
              <tr>
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Artworks</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tags.map((tag) => (
                <tr
                  key={tag.id}
                  className="border-b border-neutral-100 dark:border-neutral-800"
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
                      <span>#{tag.name}</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {editId === tag.id ? (
                      <select
                        value={editType}
                        onChange={(e) => setEditType(e.target.value)}
                        className="rounded border border-blue-400 px-2 py-1 text-sm dark:bg-neutral-900"
                      >
                        {TAG_TYPES.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span
                        className={`rounded px-2 py-0.5 text-xs ${
                          tag.type === "character"
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            : tag.type === "artist"
                              ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400"
                              : tag.type === "meta"
                                ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
                                : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
                        }`}
                      >
                        {tag.type}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 tabular-nums">
                    {tag.artwork_count}
                  </td>
                  <td className="px-3 py-2">
                    {editId === tag.id ? (
                      <div className="flex gap-2">
                        <button
                          onClick={saveEdit}
                          className="text-blue-600 hover:underline"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditId(null)}
                          className="text-neutral-400 hover:underline"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button
                          onClick={() => startEdit(tag)}
                          className="text-blue-600 hover:underline"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(tag.id, tag.name)}
                          className="text-red-500 hover:underline"
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {tags.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-3 py-8 text-center text-neutral-400"
                  >
                    No tags yet.
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
