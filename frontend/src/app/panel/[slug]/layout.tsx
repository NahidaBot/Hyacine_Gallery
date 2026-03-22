"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import TelegramLoginButton from "@/components/TelegramLoginButton";
import {
  clearToken,
  fetchAuthConfig,
  fetchMe,
  loginWithTelegram,
  passkeyAuthBegin,
  passkeyAuthComplete,
  prepareAuthOptions,
  saveToken,
  type TelegramAuthResult,
} from "@/lib/admin-api";

type AuthState = "loading" | "authenticated" | "unauthenticated";
type PasskeyStep = "idle" | "identifier" | "waiting";

export default function PanelLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { slug } = useParams<{ slug: string }>();
  const pathname = usePathname();
  const base = `/panel/${slug}`;

  const [authState, setAuthState] = useState<AuthState>("loading");
  const [role, setRole] = useState<string>("");
  const [botUsername, setBotUsername] = useState("");
  const [loginError, setLoginError] = useState("");

  // Passkey 登录状态
  const [passkeyStep, setPasskeyStep] = useState<PasskeyStep>("idle");
  const [passkeyIdentifier, setPasskeyIdentifier] = useState("");
  const [passkeyError, setPasskeyError] = useState("");

  // 验证现有 token
  useEffect(() => {
    fetchMe()
      .then((me) => {
        setRole(me.role);
        setAuthState("authenticated");
      })
      .catch(() => {
        clearToken();
        setAuthState("unauthenticated");
      });
  }, []);

  // 未登录时获取 bot username
  useEffect(() => {
    if (authState !== "unauthenticated") return;
    fetchAuthConfig()
      .then((cfg) => setBotUsername(cfg.bot_username))
      .catch(() => {});
  }, [authState]);

  const handleTelegramAuth = useCallback(async (user: TelegramAuthResult) => {
    setLoginError("");
    try {
      const { access_token, role: r } = await loginWithTelegram(user);
      saveToken(access_token);
      setRole(r);
      setAuthState("authenticated");
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "登录失败，请重试");
    }
  }, []);

  const handlePasskeyLogin = useCallback(async () => {
    if (!passkeyIdentifier.trim()) return;
    setPasskeyError("");
    setPasskeyStep("waiting");
    try {
      const rawOptions = await passkeyAuthBegin(passkeyIdentifier.trim());
      const options = prepareAuthOptions(rawOptions);
      const credential = await navigator.credentials.get({ publicKey: options });
      if (!credential || !(credential instanceof PublicKeyCredential)) {
        throw new Error("未获取到凭据");
      }
      const { access_token, role: r } = await passkeyAuthComplete(
        credential,
        passkeyIdentifier.trim(),
      );
      saveToken(access_token);
      setRole(r);
      setAuthState("authenticated");
    } catch (err) {
      setPasskeyError(err instanceof Error ? err.message : "Passkey 验证失败");
      setPasskeyStep("identifier");
    }
  }, [passkeyIdentifier]);

  const handleLogout = useCallback(() => {
    clearToken();
    setRole("");
    setAuthState("unauthenticated");
    setPasskeyStep("idle");
  }, []);

  if (authState === "loading") {
    return null;
  }

  if (authState === "unauthenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 dark:bg-neutral-950">
        <div className="w-full max-w-sm rounded-xl border border-neutral-200 bg-white p-8 text-center shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
          <h1 className="mb-2 text-xl font-bold">Hyacine Gallery</h1>
          <p className="mb-6 text-sm text-neutral-500">管理面板 — 请登录</p>

          {passkeyStep === "idle" && (
            <>
              {botUsername ? (
                <div className="flex justify-center">
                  <TelegramLoginButton
                    botUsername={botUsername}
                    onAuth={handleTelegramAuth}
                  />
                </div>
              ) : (
                <p className="text-sm text-neutral-400">正在加载登录组件...</p>
              )}

              <div className="mt-4">
                <button
                  onClick={() => setPasskeyStep("identifier")}
                  className="text-sm text-blue-500 hover:text-blue-700"
                >
                  使用 Passkey 登录
                </button>
              </div>
            </>
          )}

          {(passkeyStep === "identifier" || passkeyStep === "waiting") && (
            <div className="space-y-3">
              <p className="text-sm text-neutral-600">
                输入 Telegram 用户名或邮箱
              </p>
              <input
                value={passkeyIdentifier}
                onChange={(e) => setPasskeyIdentifier(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handlePasskeyLogin()}
                placeholder="用户名 / 邮箱"
                disabled={passkeyStep === "waiting"}
                className="w-full rounded border border-neutral-200 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800"
              />
              <button
                onClick={handlePasskeyLogin}
                disabled={passkeyStep === "waiting"}
                className="w-full rounded bg-blue-600 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {passkeyStep === "waiting" ? "等待设备验证..." : "继续"}
              </button>
              <button
                onClick={() => {
                  setPasskeyStep("idle");
                  setPasskeyError("");
                }}
                className="text-xs text-neutral-400 hover:text-neutral-600"
              >
                返回
              </button>
            </div>
          )}

          {(loginError || passkeyError) && (
            <p className="mt-4 text-sm text-red-500">
              {loginError || passkeyError}
            </p>
          )}

          <p className="mt-6 text-xs text-neutral-400">
            需要 Telegram 账号且已被站长授权
          </p>
        </div>
      </div>
    );
  }

  const nav = [
    { href: base, label: "仪表盘", ownerOnly: false },
    { href: `${base}/artworks`, label: "作品管理", ownerOnly: false },
    { href: `${base}/image-search`, label: "以图搜图", ownerOnly: false },
    { href: `${base}/tags`, label: "标签管理", ownerOnly: false },
    { href: `${base}/tag-types`, label: "标签类型", ownerOnly: false },
    { href: `${base}/bot`, label: "Bot 设置", ownerOnly: false },
    { href: `${base}/bot/channels`, label: "Bot 频道", ownerOnly: false },
    { href: `${base}/bot/logs`, label: "发布记录", ownerOnly: false },
    { href: `${base}/queue`, label: "发布队列", ownerOnly: false },
    { href: `${base}/links`, label: "友情链接", ownerOnly: false },
    { href: `${base}/users`, label: "用户管理", ownerOnly: true },
    { href: `${base}/account`, label: "账户设置", ownerOnly: false },
  ].filter((item) => !item.ownerOnly || role === "owner");

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
            onClick={handleLogout}
            className="text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
          >
            退出登录
          </button>
        </div>
      </aside>
      <div className="flex-1 p-6">{children}</div>
    </div>
  );
}
