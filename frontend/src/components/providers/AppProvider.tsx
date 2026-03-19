"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

// ── 类型定义 ──

type ThemeMode = "light" | "dark" | "system";
type NsfwMode = "hide" | "show" | "only";
type AiMode = "hide" | "show" | "only";

interface AppContextValue {
  theme: ThemeMode;
  setTheme: (t: ThemeMode) => void;
  nsfwMode: NsfwMode;
  setNsfwMode: (m: NsfwMode) => void;
  aiMode: AiMode;
  setAiMode: (m: AiMode) => void;
  columns: number;
  setColumns: (n: number) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}

// ── Provider 组件 ──

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>("system");
  const [nsfwMode, setNsfwModeState] = useState<NsfwMode>("hide");
  const [aiMode, setAiModeState] = useState<AiMode>("show");
  const [columns, setColumnsState] = useState(5);
  const [mounted, setMounted] = useState(false);

  // 挂载时从 localStorage 加载设置
  useEffect(() => {
    const savedTheme = localStorage.getItem("theme") as ThemeMode | null;
    const savedNsfw = localStorage.getItem("nsfw_mode") as NsfwMode | null;
    const savedAi = localStorage.getItem("ai_mode") as AiMode | null;
    const savedCols = localStorage.getItem("columns");
    if (savedTheme) setThemeState(savedTheme);
    if (savedNsfw) setNsfwModeState(savedNsfw);
    if (savedAi) setAiModeState(savedAi);
    if (savedCols) {
      setColumnsState(Number(savedCols));
    } else {
      // 默认：移动端 2 列，桌面端 5 列
      setColumnsState(window.innerWidth < 640 ? 2 : 5);
    }
    setMounted(true);
  }, []);

  // 在 <html> 上应用 dark 类
  useEffect(() => {
    if (!mounted) return;

    const applyDark = (dark: boolean) => {
      document.documentElement.classList.toggle("dark", dark);
    };

    if (theme === "dark") {
      applyDark(true);
    } else if (theme === "light") {
      applyDark(false);
    } else {
      // 跟随系统
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      applyDark(mq.matches);
      const handler = (e: MediaQueryListEvent) => applyDark(e.matches);
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
  }, [theme, mounted]);

  const setTheme = useCallback((t: ThemeMode) => {
    setThemeState(t);
    localStorage.setItem("theme", t);
  }, []);

  const setNsfwMode = useCallback((m: NsfwMode) => {
    setNsfwModeState(m);
    localStorage.setItem("nsfw_mode", m);
  }, []);

  const setAiMode = useCallback((m: AiMode) => {
    setAiModeState(m);
    localStorage.setItem("ai_mode", m);
  }, []);

  const setColumns = useCallback((n: number) => {
    setColumnsState(n);
    localStorage.setItem("columns", String(n));
  }, []);

  return (
    <AppContext.Provider value={{ theme, setTheme, nsfwMode, setNsfwMode, aiMode, setAiMode, columns, setColumns }}>
      {mounted ? children : <div style={{ visibility: "hidden" }}>{children}</div>}
    </AppContext.Provider>
  );
}
