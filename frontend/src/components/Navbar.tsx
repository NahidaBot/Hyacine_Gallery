"use client";

import Link from "next/link";
import { useApp } from "@/components/providers/AppProvider";

const THEME_LABELS = { light: "Light", dark: "Dark", system: "Auto" } as const;
const THEME_CYCLE: ("light" | "dark" | "system")[] = ["light", "dark", "system"];

const NSFW_LABELS = { hide: "SFW", show: "All", only: "NSFW" } as const;
const NSFW_CYCLE: ("hide" | "show" | "only")[] = ["hide", "show", "only"];

export function Navbar() {
  const { theme, setTheme, nsfwMode, setNsfwMode } = useApp();

  function cycleTheme() {
    const idx = THEME_CYCLE.indexOf(theme);
    setTheme(THEME_CYCLE[(idx + 1) % THEME_CYCLE.length]);
  }

  function cycleNsfw() {
    const idx = NSFW_CYCLE.indexOf(nsfwMode);
    setNsfwMode(NSFW_CYCLE[(idx + 1) % NSFW_CYCLE.length]);
  }

  const btnCls =
    "rounded border border-neutral-300 px-2.5 py-1 text-xs font-medium transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800";

  return (
    <header className="border-b border-neutral-200 dark:border-neutral-800">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
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

        {/* Right: toggle buttons */}
        <div className="flex items-center gap-2">
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
        </div>
      </nav>
    </header>
  );
}
