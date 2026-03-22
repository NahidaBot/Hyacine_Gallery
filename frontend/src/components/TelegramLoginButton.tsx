"use client";

import { useEffect, useRef } from "react";
import type { TelegramAuthResult } from "@/lib/admin-api";

// 扩展 window 类型，允许挂载 Telegram Widget 回调
declare global {
  interface Window {
    __onTelegramAuth?: (user: TelegramAuthResult) => void;
  }
}

interface Props {
  botUsername: string;
  onAuth: (user: TelegramAuthResult) => void;
}

/**
 * Telegram Login Widget 组件。
 * 通过动态加载官方 Widget 脚本实现，回调通过 window.__onTelegramAuth 传递。
 *
 * 注意：Widget 要求 HTTPS 或 localhost，且需在 BotFather 通过 /setdomain 授权域名。
 */
export default function TelegramLoginButton({ botUsername, onAuth }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!botUsername || !containerRef.current) return;

    // 挂载全局回调（Widget 会调用 window.__onTelegramAuth(user)）
    window.__onTelegramAuth = onAuth;

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", botUsername);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-onauth", "__onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");

    containerRef.current.appendChild(script);

    return () => {
      delete window.__onTelegramAuth;
      script.remove();
    };
  }, [botUsername, onAuth]);

  return <div ref={containerRef} />;
}
