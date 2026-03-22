"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { Artwork, ArtworkImage } from "@/types";
import {
  GenericPlatformIcon,
  PLATFORM_COLORS,
  PLATFORM_ICON_MAP,
} from "@/components/icons/PlatformIcons";

const THUMB_MAX_EDGE = 1536;
const SWIPE_THRESHOLD = 0.15;

function buildSrcSet(img: ArtworkImage) {
  const thumb = img.url_thumb || "";
  const original = img.url_original || "";
  if (!thumb || !original || thumb === original) return undefined;
  const origW = img.width || 0;
  const origH = img.height || 0;
  const longEdge = Math.max(origW, origH);
  const thumbW =
    longEdge > THUMB_MAX_EDGE
      ? Math.round(origW * (THUMB_MAX_EDGE / longEdge))
      : origW;
  return thumbW > 0 && origW > thumbW
    ? `${thumb} ${thumbW}w, ${original} ${origW}w`
    : undefined;
}

function wrap(i: number, n: number) {
  return ((i % n) + n) % n;
}

function PageImage({ img }: { img: ArtworkImage }) {
  const s = img.url_thumb || img.url_original || "";
  if (!s) return <div className="flex size-full items-center justify-center text-neutral-300">暂无图片</div>;
  return (
    /* eslint-disable-next-line @next/next/no-img-element */
    <img
      src={s}
      srcSet={buildSrcSet(img)}
      sizes="100vw"
      alt=""
      className="size-full object-contain"
      loading="lazy"
      draggable={false}
    />
  );
}

export function ArtworkCard({ artwork }: { artwork: Artwork }) {
  const images = artwork.images;
  const n = images.length;

  const [page, setPage] = useState(0);
  const [hovering, setHovering] = useState(false);

  // shift 控制三面板视口的 CSS translateX
  // 0 = 显示中间（当前），-1 = 显示左侧（上一页），+1 = 显示右侧（下一页）
  const [shift, setShift] = useState(0);
  const [animate, setAnimate] = useState(false);

  // 触摸拖拽偏移量（像素），未拖拽时为 0
  const [dragPx, setDragPx] = useState(0);
  const dragging = useRef(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const touchRef = useRef({ startX: 0, startY: 0, locked: false, horizontal: false });

  const firstImg = images[0];
  const firstW = firstImg?.width || 0;
  const firstH = firstImg?.height || 0;
  const aspectRatio = firstW > 0 && firstH > 0 ? `${firstW}/${firstH}` : undefined;

  const hasBadges = artwork.is_nsfw || artwork.is_ai;

  // 由按钮 / 滚轮触发，动画切换到上一页/下一页
  function animateTo(dir: -1 | 1) {
    if (animate) return;
    setAnimate(true);
    setShift(dir); // CSS transition moves the panel
  }

  // CSS 过渡结束后，提交页面切换并重置状态
  function onTransitionEnd() {
    if (shift === 0) return;
    setAnimate(false);
    setPage((p) => wrap(p + shift, n));
    setShift(0);
  }

  // 滚轮事件
  useEffect(() => {
    const el = containerRef.current;
    if (!el || n <= 1) return;
    let cooldown = false;
    function onWheel(e: WheelEvent) {
      if (Math.abs(e.deltaY) < 5 || cooldown) return;
      e.preventDefault();
      cooldown = true;
      setTimeout(() => (cooldown = false), 350);
      animateTo(e.deltaY > 0 ? 1 : -1);
    }
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  });

  // 触摸事件
  useEffect(() => {
    const el = containerRef.current;
    if (!el || n <= 1) return;

    function onStart(e: TouchEvent) {
      touchRef.current = { startX: e.touches[0].clientX, startY: e.touches[0].clientY, locked: false, horizontal: false };
      dragging.current = false;
      setDragPx(0);
      setAnimate(false);
    }

    function onMove(e: TouchEvent) {
      const t = touchRef.current;
      const dx = e.touches[0].clientX - t.startX;
      const dy = e.touches[0].clientY - t.startY;
      if (!t.locked) {
        if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
          t.locked = true;
          t.horizontal = Math.abs(dx) >= Math.abs(dy);
        } else return;
      }
      if (!t.horizontal) return;
      e.preventDefault();
      dragging.current = true;
      setDragPx(dx);
    }

    function onEnd() {
      if (!dragging.current) { setDragPx(0); return; }
      const width = el!.offsetWidth;
      const ratio = dragPx / width;
      dragging.current = false;
      setDragPx(0);
      if (Math.abs(ratio) > SWIPE_THRESHOLD) {
        animateTo(ratio < 0 ? 1 : -1);
      }
    }

    el.addEventListener("touchstart", onStart, { passive: true });
    el.addEventListener("touchmove", onMove, { passive: false });
    el.addEventListener("touchend", onEnd, { passive: true });
    el.addEventListener("touchcancel", onEnd, { passive: true });
    return () => {
      el.removeEventListener("touchstart", onStart);
      el.removeEventListener("touchmove", onMove);
      el.removeEventListener("touchend", onEnd);
      el.removeEventListener("touchcancel", onEnd);
    };
  });

  // 三面板布局：[上一页] [当前] [下一页]，各占 300% 宽条带的 33.33%
  // 默认：translateX(-33.33%) 显示中间面板
  // shift=-1 → translateX(0%) 显示上一页；shift=+1 → translateX(-66.67%) 显示下一页
  const basePct = -100 / 3;
  let translateValue: string;

  if (dragging.current && dragPx !== 0) {
    translateValue = `calc(${basePct}% + ${dragPx}px)`;
  } else {
    translateValue = `${basePct + shift * basePct}%`;
  }

  return (
    <Link
      href={`/artwork/${artwork.id}`}
      className="group inline-block w-full overflow-hidden rounded-lg border border-neutral-200 transition-shadow hover:shadow-md dark:border-neutral-800"
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => { setHovering(false); if (!animate) setPage(0); }}
      draggable={false}
    >
      <div
        className="relative w-full overflow-hidden bg-neutral-100 dark:bg-neutral-900"
        style={aspectRatio ? { aspectRatio } : undefined}
        ref={containerRef}
      >
        {n <= 1 ? (
          (() => {
            const s = firstImg?.url_thumb || firstImg?.url_original || "";
            return s ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img src={s} srcSet={firstImg ? buildSrcSet(firstImg) : undefined} sizes="100vw"
                alt={artwork.title || artwork.pid}
                className="block w-full transition-transform group-hover:scale-105"
                loading="eager" draggable={false}
              />
            ) : (
              <div className="flex aspect-square items-center justify-center text-neutral-300">暂无图片</div>
            );
          })()
        ) : (
          <div
            className="absolute inset-0 flex"
            style={{
              width: "300%",
              transform: `translateX(${translateValue})`,
              transition: animate ? "transform 0.25s ease-out" : "none",
            }}
            onTransitionEnd={onTransitionEnd}
          >
            <div className="h-full" style={{ width: "33.333%" }}>
              <PageImage img={images[wrap(page - 1, n)]} />
            </div>
            <div className="h-full" style={{ width: "33.333%" }}>
              <PageImage img={images[page]} />
            </div>
            <div className="h-full" style={{ width: "33.333%" }}>
              <PageImage img={images[wrap(page + 1, n)]} />
            </div>
          </div>
        )}

        {hasBadges && (
          <div className="absolute right-[4%] top-[4%] flex gap-[0.3em] text-[clamp(10px,3cqi,18px)]">
            {artwork.is_nsfw && (
              <span className="rounded border border-red-500/80 px-[0.4em] py-[0.1em] font-medium text-red-500/80 transition-colors group-hover:bg-red-600/80 group-hover:text-white">NSFW</span>
            )}
            {artwork.is_ai && (
              <span className="rounded border border-blue-400/80 px-[0.4em] py-[0.1em] font-medium text-blue-400/80 transition-colors group-hover:bg-blue-600/80 group-hover:text-white">AI</span>
            )}
          </div>
        )}

        {n > 1 && (
          <>
            <span className="absolute left-[4%] top-[4%] max-w-16 rounded bg-black/60 px-[0.4em] py-[0.15em] text-[clamp(10px,3cqi,18px)] font-medium tabular-nums text-white">
              {page + 1}/{n}
            </span>
            {hovering && (
              <>
                <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); animateTo(-1); }}
                  className="absolute left-1 top-1/2 flex size-6 -translate-y-1/2 items-center justify-center rounded-full bg-black/50 text-sm text-white transition-colors hover:bg-black/70">
                  &lsaquo;
                </button>
                <button onClick={(e) => { e.preventDefault(); e.stopPropagation(); animateTo(1); }}
                  className="absolute right-1 top-1/2 flex size-6 -translate-y-1/2 items-center justify-center rounded-full bg-black/50 text-sm text-white transition-colors hover:bg-black/70">
                  &rsaquo;
                </button>
              </>
            )}
          </>
        )}
      </div>

      <div className="flex items-end justify-between gap-1 p-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{artwork.title_zh || artwork.title || artwork.pid}</p>
          {artwork.author ? (
            <Link
              href={`/author/${encodeURIComponent(artwork.author)}`}
              onClick={(e) => e.stopPropagation()}
              className="block truncate text-xs text-neutral-500 hover:text-blue-500 hover:underline"
            >
              {artwork.author}
            </Link>
          ) : (
            <p className="truncate text-xs text-neutral-500">&nbsp;</p>
          )}
        </div>
        {artwork.sources?.length > 0 && (
          <div className="flex shrink-0 items-center gap-1">
            {artwork.sources.map((s) => {
              const Icon = PLATFORM_ICON_MAP[s.platform];
              const colorCls = PLATFORM_COLORS[s.platform] ?? "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300";
              return (
                <a key={s.id} href={s.source_url} target="_blank" rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className={`transition-colors ${colorCls}`}
                  title={`${s.platform} / ${s.pid}`}>
                  {Icon ? <Icon className="size-6" /> : <GenericPlatformIcon platform={s.platform} className="size-6" />}
                </a>
              );
            })}
          </div>
        )}
      </div>
    </Link>
  );
}
