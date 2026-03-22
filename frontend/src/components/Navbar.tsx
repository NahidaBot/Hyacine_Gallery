"use client";

import Link from "next/link";
import { useApp } from "@/components/providers/AppProvider";

const THEME_LABELS = { light: "亮色", dark: "暗色", system: "自动" } as const;
const THEME_CYCLE: ("light" | "dark" | "system")[] = ["light", "dark", "system"];

const NSFW_LABELS = { hide: "安全", show: "全部", only: "仅NSFW" } as const;
const NSFW_CYCLE: ("hide" | "show" | "only")[] = ["hide", "show", "only"];

const AI_LABELS = { hide: "无AI", show: "全部", only: "仅AI" } as const;
const AI_CYCLE: ("hide" | "show" | "only")[] = ["show", "hide", "only"];

const COLUMN_STOPS = [2, 3, 4, 5, 6, 8, 10];

export function Navbar() {
  const { theme, setTheme, nsfwMode, setNsfwMode, aiMode, setAiMode, columns, setColumns } = useApp();

  // 将滑块索引 (0-6) 映射到列数档位
  const colIndex = COLUMN_STOPS.indexOf(columns);
  const sliderValue = colIndex >= 0 ? colIndex : 3; // 默认 5 列

  function cycleTheme() {
    const idx = THEME_CYCLE.indexOf(theme);
    setTheme(THEME_CYCLE[(idx + 1) % THEME_CYCLE.length]);
  }

  function cycleNsfw() {
    const idx = NSFW_CYCLE.indexOf(nsfwMode);
    setNsfwMode(NSFW_CYCLE[(idx + 1) % NSFW_CYCLE.length]);
  }

  function cycleAi() {
    const idx = AI_CYCLE.indexOf(aiMode);
    setAiMode(AI_CYCLE[(idx + 1) % AI_CYCLE.length]);
  }

  const btnCls =
    "rounded border border-neutral-300 px-2.5 py-1 text-xs font-medium transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800";

  return (
    <header className="border-b border-neutral-200 dark:border-neutral-800">
      <nav className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 sm:px-6 sm:py-3">
        {/* 左侧：logo + 导航链接 */}
        <div className="flex items-center gap-4 sm:gap-6">
          <Link href="/" className="text-lg font-bold sm:text-xl">
            Hyacine Gallery
          </Link>
          <div className="flex gap-3 text-sm sm:gap-4">
            <Link href="/" className="hover:underline">
              画廊
            </Link>
            <Link href="/tags" className="hover:underline">
              标签
            </Link>
            <Link href="/links" className="hover:underline">
              友链
            </Link>
            <Link href="/about" className="hover:underline">
              关于
            </Link>
          </div>
        </div>

        {/* 右侧：列数滑块 + 切换按钮 */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-neutral-500">{columns}列</span>
            <input
              type="range"
              min={0}
              max={COLUMN_STOPS.length - 1}
              value={sliderValue}
              onChange={(e) => setColumns(COLUMN_STOPS[Number(e.target.value)])}
              className="h-1 w-16 cursor-pointer accent-neutral-500 sm:w-20"
              title={`${columns} 列`}
            />
          </div>
          <div className="hidden h-4 w-px bg-neutral-300 sm:block dark:bg-neutral-700" />
          <button onClick={cycleTheme} className={btnCls} title="切换主题">
            {theme === "dark" ? "\u{1F319}" : theme === "light" ? "\u{2600}\u{FE0F}" : "\u{1F4BB}"}{" "}
            <span className="hidden sm:inline">{THEME_LABELS[theme]}</span>
          </button>
          <button
            onClick={cycleNsfw}
            className={`${btnCls} ${
              nsfwMode === "only"
                ? "border-red-400 text-red-500 dark:border-red-600 dark:text-red-400"
                : nsfwMode === "show"
                  ? "border-yellow-400 text-yellow-600 dark:border-yellow-600 dark:text-yellow-400"
                  : ""
            }`}
            title="切换 NSFW 过滤"
          >
            {nsfwMode === "hide" ? "\u{1F512}" : nsfwMode === "show" ? "\u{1F513}" : "\u{1F51E}"}{" "}
            <span className="hidden sm:inline">{NSFW_LABELS[nsfwMode]}</span>
          </button>
          <button
            onClick={cycleAi}
            className={`${btnCls} ${
              aiMode === "only"
                ? "border-blue-400 text-blue-500 dark:border-blue-600 dark:text-blue-400"
                : aiMode === "hide"
                  ? "border-orange-400 text-orange-600 dark:border-orange-600 dark:text-orange-400"
                  : ""
            }`}
            title="切换 AI 过滤"
          >
            {aiMode === "show" ? "\u{1F916}" : aiMode === "hide" ? "\u{1F3A8}" : "\u{2728}"}{" "}
            <span className="hidden sm:inline">{AI_LABELS[aiMode]}</span>
          </button>
        </div>
      </nav>
    </header>
  );
}
