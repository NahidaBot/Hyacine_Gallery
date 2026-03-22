"use client";

import { useEffect, useState } from "react";
import type { PasskeyCredential } from "@/types";
import {
  adminDeleteUserCredential,
  adminFetchUserCredentials,
  passkeyRegisterBegin,
  passkeyRegisterComplete,
  prepareCreationOptions,
} from "@/lib/admin-api";

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

interface Props {
  userId: number;
}

export default function PasskeyManager({ userId }: Props) {
  const [creds, setCreds] = useState<PasskeyCredential[]>([]);
  const [loading, setLoading] = useState(true);
  const [registering, setRegistering] = useState(false);
  const [deviceName, setDeviceName] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    adminFetchUserCredentials(userId)
      .then(setCreds)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [userId]);

  async function handleRegister() {
    setError("");
    setSuccess("");
    setRegistering(true);
    try {
      // 1. 获取注册 options
      const rawOptions = await passkeyRegisterBegin();
      const creationOptions = prepareCreationOptions(rawOptions);

      // 2. 调用浏览器 WebAuthn API
      const credential = await navigator.credentials.create({
        publicKey: creationOptions,
      });
      if (!credential || !(credential instanceof PublicKeyCredential)) {
        throw new Error("未获取到凭据");
      }

      // 3. 发送到后端完成注册
      await passkeyRegisterComplete(credential, deviceName || "未命名设备");

      setSuccess("Passkey 绑定成功！");
      setDeviceName("");

      // 刷新列表
      const updated = await adminFetchUserCredentials(userId);
      setCreds(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRegistering(false);
    }
  }

  async function handleDelete(credId: number, name: string) {
    if (!confirm(`确认删除 Passkey「${name}」？`)) return;
    try {
      await adminDeleteUserCredential(userId, credId);
      setCreds((prev) => prev.filter((c) => c.id !== credId));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="space-y-4">
      <h3 className="font-semibold">我的 Passkey</h3>

      {loading && <p className="text-sm text-neutral-400">加载中...</p>}

      {error && <p className="text-sm text-red-500">{error}</p>}
      {success && <p className="text-sm text-green-600">{success}</p>}

      {!loading && creds.length === 0 && (
        <p className="text-sm text-neutral-400">暂未绑定任何 Passkey</p>
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
              onClick={() => handleDelete(c.id, c.device_name)}
              className="text-xs text-red-400 hover:text-red-600"
            >
              删除
            </button>
          </div>
        ))}
      </div>

      <div className="flex gap-2 pt-2">
        <input
          value={deviceName}
          onChange={(e) => setDeviceName(e.target.value)}
          placeholder="设备名称（可选）"
          className="flex-1 rounded border border-neutral-200 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-800"
        />
        <button
          onClick={handleRegister}
          disabled={registering}
          className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {registering ? "注册中..." : "绑定新 Passkey"}
        </button>
      </div>
    </div>
  );
}
