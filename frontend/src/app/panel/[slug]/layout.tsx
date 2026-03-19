"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";

// 通过 useSyncExternalStore 同步检查 token，避免 lint 问题
function useTokenReady(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => {
      if (typeof window === "undefined") return false;
      const stored = localStorage.getItem("admin_token");
      if (!stored) {
        const token = prompt("请输入管理员令牌：");
        if (token) localStorage.setItem("admin_token", token);
      }
      return true;
    },
    () => false,
  );
}

export default function PanelLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { slug } = useParams<{ slug: string }>();
  const pathname = usePathname();
  const base = `/panel/${slug}`;

  const ready = useTokenReady();

  if (!ready) return null;

  const nav = [
    { href: base, label: "仪表盘" },
    { href: `${base}/artworks`, label: "作品管理" },
    { href: `${base}/image-search`, label: "以图搜图" },
    { href: `${base}/tags`, label: "标签管理" },
    { href: `${base}/tag-types`, label: "标签类型" },
    { href: `${base}/bot`, label: "Bot 设置" },
    { href: `${base}/bot/channels`, label: "Bot 频道" },
    { href: `${base}/bot/logs`, label: "发布记录" },
  ];

  return (
    <div className="flex min-h-[calc(100vh-65px)]">
      <aside className="w-48 shrink-0 border-r border-neutral-200 p-4 dark:border-neutral-800">
        <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-neutral-400">
          管理面板
        </h2>
        <nav className="flex flex-col gap-1">
          {nav.map((item) => {
            const isExact = pathname === item.href;
            const isChild =
              item.href !== base &&
              pathname.startsWith(item.href + "/") &&
              !nav.some(
                (other) =>
                  other.href !== item.href &&
                  other.href.startsWith(item.href + "/") &&
                  (pathname === other.href ||
                    pathname.startsWith(other.href + "/")),
              );
            const active = isExact || isChild;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? "bg-neutral-100 font-medium dark:bg-neutral-800"
                    : "hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-6 border-t border-neutral-200 pt-4 dark:border-neutral-800">
          <button
            onClick={() => {
              localStorage.removeItem("admin_token");
              const token = prompt("请输入管理员令牌：");
              if (token) localStorage.setItem("admin_token", token);
              window.location.reload();
            }}
            className="text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
          >
            更换令牌
          </button>
        </div>
      </aside>
      <div className="flex-1 p-6">{children}</div>
    </div>
  );
}
