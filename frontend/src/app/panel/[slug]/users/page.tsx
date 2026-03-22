"use client";

import { useEffect, useState } from "react";
import type { AdminUser, PasskeyCredential } from "@/types";
import {
  adminCreateUser,
  adminDeleteUser,
  adminDeleteUserCredential,
  adminFetchUserCredentials,
  adminFetchUsers,
  adminUpdateUser,
} from "@/lib/admin-api";

// ── 工具 ─────────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Passkey 凭据弹窗 ─────────────────────────────────────────────────────────

function PasskeyModal({
  user,
  onClose,
}: {
  user: AdminUser;
  onClose: () => void;
}) {
  const [creds, setCreds] = useState<PasskeyCredential[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    adminFetchUserCredentials(user.id)
      .then(setCreds)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [user.id]);

  async function handleDelete(credId: number) {
    if (!confirm("确认删除该 Passkey？")) return;
    try {
      await adminDeleteUserCredential(user.id, credId);
      setCreds((prev) => prev.filter((c) => c.id !== credId));
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl border border-neutral-200 bg-white p-6 shadow-xl dark:border-neutral-700 dark:bg-neutral-900">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold">
            {user.tg_username || `User #${user.id}`} 的 Passkey
          </h3>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600"
          >
            ✕
          </button>
        </div>

        {loading && <p className="text-sm text-neutral-400">加载中...</p>}
        {error && <p className="text-sm text-red-500">{error}</p>}

        {!loading && creds.length === 0 && (
          <p className="text-sm text-neutral-400">暂无绑定的 Passkey</p>
        )}

        <div className="space-y-2">
          {creds.map((c) => (
            <div
              key={c.id}
              className="flex items-center justify-between rounded border border-neutral-100 p-3 dark:border-neutral-800"
            >
              <div>
                <p className="text-sm font-medium">{c.device_name || "未命名设备"}</p>
                <p className="text-xs text-neutral-400">
                  创建：{fmtDate(c.created_at)}
                  {c.last_used_at && `  ·  最后使用：${fmtDate(c.last_used_at)}`}
                </p>
              </div>
              <button
                onClick={() => handleDelete(c.id)}
                className="text-xs text-red-400 hover:text-red-600"
              >
                删除
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── 编辑弹窗 ──────────────────────────────────────────────────────────────────

function EditModal({
  user,
  onSave,
  onClose,
}: {
  user: AdminUser;
  onSave: (updated: AdminUser) => void;
  onClose: () => void;
}) {
  const [tgUsername, setTgUsername] = useState(user.tg_username);
  const [email, setEmail] = useState(user.email ?? "");
  const [role, setRole] = useState<"admin" | "owner">(user.role);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const updated = await adminUpdateUser(user.id, {
        tg_username: tgUsername,
        email: email || null,
        role,
      });
      onSave(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-xl border border-neutral-200 bg-white p-6 shadow-xl dark:border-neutral-700 dark:bg-neutral-900">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold">编辑用户 #{user.id}</h3>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600"
          >
            ✕
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs text-neutral-500">
              Telegram 用户名
            </label>
            <input
              value={tgUsername}
              onChange={(e) => setTgUsername(e.target.value)}
              className="w-full rounded border border-neutral-200 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-500">邮箱</label>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              className="w-full rounded border border-neutral-200 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-500">角色</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as "admin" | "owner")}
              className="w-full rounded border border-neutral-200 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            >
              <option value="admin">管理员</option>
              <option value="owner">站长</option>
            </select>
          </div>
        </div>

        {error && <p className="mt-3 text-sm text-red-500">{error}</p>}

        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded px-3 py-1.5 text-sm text-neutral-500 hover:bg-neutral-50 dark:hover:bg-neutral-800"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── 添加用户弹窗 ──────────────────────────────────────────────────────────────

function CreateModal({
  onCreated,
  onClose,
}: {
  onCreated: (user: AdminUser) => void;
  onClose: () => void;
}) {
  const [tgId, setTgId] = useState("");
  const [tgUsername, setTgUsername] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"admin" | "owner">("admin");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleCreate() {
    setSaving(true);
    setError("");
    try {
      const user = await adminCreateUser({
        tg_id: tgId ? Number(tgId) : null,
        tg_username: tgUsername,
        email: email || null,
        role,
      });
      onCreated(user);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-xl border border-neutral-200 bg-white p-6 shadow-xl dark:border-neutral-700 dark:bg-neutral-900">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold">添加用户</h3>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600"
          >
            ✕
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs text-neutral-500">
              Telegram ID
            </label>
            <input
              value={tgId}
              onChange={(e) => setTgId(e.target.value)}
              placeholder="可选"
              className="w-full rounded border border-neutral-200 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-500">
              Telegram 用户名
            </label>
            <input
              value={tgUsername}
              onChange={(e) => setTgUsername(e.target.value)}
              className="w-full rounded border border-neutral-200 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-500">邮箱</label>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              placeholder="可选"
              className="w-full rounded border border-neutral-200 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-neutral-500">角色</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as "admin" | "owner")}
              className="w-full rounded border border-neutral-200 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            >
              <option value="admin">管理员</option>
              <option value="owner">站长</option>
            </select>
          </div>
        </div>

        {error && <p className="mt-3 text-sm text-red-500">{error}</p>}

        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded px-3 py-1.5 text-sm text-neutral-500 hover:bg-neutral-50 dark:hover:bg-neutral-800"
          >
            取消
          </button>
          <button
            onClick={handleCreate}
            disabled={saving}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "创建中..." : "创建"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── 主页面 ────────────────────────────────────────────────────────────────────

export default function UsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editUser, setEditUser] = useState<AdminUser | null>(null);
  const [passkeyUser, setPasskeyUser] = useState<AdminUser | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    adminFetchUsers()
      .then(setUsers)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(user: AdminUser) {
    if (
      !confirm(
        `确认删除用户 ${user.tg_username || `#${user.id}`}？此操作不可撤销。`,
      )
    )
      return;
    try {
      await adminDeleteUser(user.id);
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  if (loading) return <p className="text-sm text-neutral-400">加载中...</p>;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">用户管理</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
        >
          + 添加用户
        </button>
      </div>

      {error && (
        <p className="mb-4 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}

      <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-700">
        <table className="w-full text-sm">
          <thead className="bg-neutral-50 dark:bg-neutral-800">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-neutral-500">
                ID
              </th>
              <th className="px-3 py-2 text-left font-medium text-neutral-500">
                Telegram
              </th>
              <th className="px-3 py-2 text-left font-medium text-neutral-500">
                邮箱
              </th>
              <th className="px-3 py-2 text-left font-medium text-neutral-500">
                角色
              </th>
              <th className="px-3 py-2 text-left font-medium text-neutral-500">
                最后登录
              </th>
              <th className="px-3 py-2 text-center font-medium text-neutral-500">
                导入数
              </th>
              <th className="px-3 py-2 text-center font-medium text-neutral-500">
                发图数
              </th>
              <th className="px-3 py-2 text-right font-medium text-neutral-500">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
            {users.map((u) => (
              <tr key={u.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800/40">
                <td className="px-3 py-2 text-neutral-400">{u.id}</td>
                <td className="px-3 py-2">
                  <div className="font-medium">{u.tg_username || "—"}</div>
                  {u.tg_id && (
                    <div className="text-xs text-neutral-400">ID: {u.tg_id}</div>
                  )}
                </td>
                <td className="px-3 py-2 text-neutral-500">
                  {u.email || "—"}
                </td>
                <td className="px-3 py-2">
                  <span
                    className={`rounded px-2 py-0.5 text-xs ${
                      u.role === "owner"
                        ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                        : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                    }`}
                  >
                    {u.role === "owner" ? "站长" : "管理员"}
                  </span>
                </td>
                <td className="px-3 py-2 text-neutral-500">
                  {fmtDate(u.last_login_at)}
                </td>
                <td className="px-3 py-2 text-center">{u.import_count}</td>
                <td className="px-3 py-2 text-center">{u.post_count}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setPasskeyUser(u)}
                      className="text-xs text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300"
                    >
                      Passkey
                    </button>
                    <button
                      onClick={() => setEditUser(u)}
                      className="text-xs text-blue-500 hover:text-blue-700"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleDelete(u)}
                      className="text-xs text-red-400 hover:text-red-600"
                    >
                      删除
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {users.length === 0 && (
          <p className="py-8 text-center text-sm text-neutral-400">暂无用户</p>
        )}
      </div>

      {editUser && (
        <EditModal
          user={editUser}
          onSave={(updated) => {
            setUsers((prev) =>
              prev.map((u) => (u.id === updated.id ? updated : u)),
            );
            setEditUser(null);
          }}
          onClose={() => setEditUser(null)}
        />
      )}

      {passkeyUser && (
        <PasskeyModal user={passkeyUser} onClose={() => setPasskeyUser(null)} />
      )}

      {showCreate && (
        <CreateModal
          onCreated={(u) => {
            setUsers((prev) => [...prev, u]);
            setShowCreate(false);
          }}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  );
}
