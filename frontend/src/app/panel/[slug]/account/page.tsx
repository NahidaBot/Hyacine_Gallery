"use client";

import { useEffect, useState } from "react";
import PasskeyManager from "@/components/PasskeyManager";
import { fetchMe } from "@/lib/admin-api";

interface Me {
  id: number;
  tg_id: number | null;
  tg_username: string;
  email: string | null;
  role: string;
}

export default function AccountPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMe()
      .then((data) => setMe(data as Me))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-neutral-400">加载中...</p>;
  if (!me) return <p className="text-sm text-red-500">无法获取用户信息</p>;

  return (
    <div className="max-w-lg space-y-8">
      <h1 className="text-xl font-bold">账户设置</h1>

      {/* 基本信息（只读展示） */}
      <section className="rounded-lg border border-neutral-200 p-5 dark:border-neutral-700">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-neutral-400">
          个人信息
        </h2>
        <dl className="space-y-2 text-sm">
          <div className="flex gap-4">
            <dt className="w-24 shrink-0 text-neutral-500">用户名</dt>
            <dd className="font-medium">{me.tg_username || "—"}</dd>
          </div>
          {me.tg_id && (
            <div className="flex gap-4">
              <dt className="w-24 shrink-0 text-neutral-500">Telegram ID</dt>
              <dd>{me.tg_id}</dd>
            </div>
          )}
          <div className="flex gap-4">
            <dt className="w-24 shrink-0 text-neutral-500">邮箱</dt>
            <dd>{me.email || "—"}</dd>
          </div>
          <div className="flex gap-4">
            <dt className="w-24 shrink-0 text-neutral-500">角色</dt>
            <dd>
              <span
                className={`rounded px-2 py-0.5 text-xs ${
                  me.role === "owner"
                    ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                    : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                }`}
              >
                {me.role === "owner" ? "站长" : "管理员"}
              </span>
            </dd>
          </div>
        </dl>
      </section>

      {/* Passkey 管理 */}
      <section className="rounded-lg border border-neutral-200 p-5 dark:border-neutral-700">
        <PasskeyManager userId={me.id} />
      </section>
    </div>
  );
}
