"use client";

import Link from "next/link";
import { useApp } from "@/components/providers/AppProvider";

const THEME_LABELS = { light: "Light", dark: "Dark", system: "Auto" } as const;
const THEME_CYCLE: ("light" | "dark" | "system")[] = ["light", "dark", "system"];

const NSFW_LABELS = { hide: "SFW", show: "All", only: "NSFW" } as const;
const NSFW_CYCLE: ("hide" | "show" | "only")[] = ["hide", "show", "only"];

const AI_LABELS = { hide: "No AI", show: "All", only: "AI" } as const;
const AI_CYCLE: ("hide" | "show" | "only")[] = ["show", "hide", "only"];

const COLUMN_STOPS = [2, 3, 4, 5, 6, 8, 10];

export function Navbar() {
  const { theme, setTheme, nsfwMode, setNsfwMode, aiMode, setAiMode, columns, setColumns } = useApp();

  // Map slider index (0-6) to column stops
  const colIndex = COLUMN_STOPS.indexOf(columns);
  const sliderValue = colIndex >= 0 ? colIndex : 3; // default to 5 cols

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
      <nav className="flex items-center justify-between px-6 py-3">
        {/* Left: logo + nav links */}
        <div className="flex items-center gap-6">
          <Link href="/" className="text-xl font-bold">
            Hyacine Gallery
          </Link>
          <div className="flex gap-4 text-sm">
            <Link href="/" className="hover:underline">
              Gallery
            </Link>
            <Link href="/tags" className="hover:underline">
              Tags
            </Link>
          </div>
        </div>

        {/* Right: columns slider + toggle buttons */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-neutral-500">{columns}col</span>
            <input
              type="range"
              min={0}
              max={COLUMN_STOPS.length - 1}
              value={sliderValue}
              onChange={(e) => setColumns(COLUMN_STOPS[Number(e.target.value)])}
              className="h-1 w-20 cursor-pointer accent-neutral-500"
              title={`${columns} columns`}
            />
          </div>
          <div className="h-4 w-px bg-neutral-300 dark:bg-neutral-700" />
          <button onClick={cycleTheme} className={btnCls} title="Toggle theme">
            {theme === "dark" ? "\u{1F319}" : theme === "light" ? "\u{2600}\u{FE0F}" : "\u{1F4BB}"}{" "}
            {THEME_LABELS[theme]}
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
            title="Toggle NSFW filter"
          >
            {nsfwMode === "hide" ? "\u{1F512}" : nsfwMode === "show" ? "\u{1F513}" : "\u{1F51E}"}{" "}
            {NSFW_LABELS[nsfwMode]}
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
            title="Toggle AI filter"
          >
            {aiMode === "show" ? "\u{1F916}" : aiMode === "hide" ? "\u{1F3A8}" : "\u{2728}"}{" "}
            {AI_LABELS[aiMode]}
          </button>
        </div>
      </nav>
    </header>
  );
}
