interface IconProps {
  className?: string;
}

export function PixivIcon({ className = "size-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M4.935 0A4.924 4.924 0 0 0 0 4.935v14.13A4.924 4.924 0 0 0 4.935 24h14.13A4.924 4.924 0 0 0 24 19.065V4.935A4.924 4.924 0 0 0 19.065 0zm7.81 4.547c2.181 0 4.058.676 5.399 1.847a6.118 6.118 0 0 1 2.116 4.66c.005 1.854-.88 3.476-2.257 4.563-1.375 1.1-3.215 1.688-5.258 1.688-2.044 0-3.505-.492-3.505-.492v4.246H7.116V5.04s2.493-.493 5.629-.493zM12.6 6.65c-1.569 0-3.36.357-3.36.357v8.245s1.685.535 3.36.535c1.26 0 2.397-.39 3.218-1.098.837-.715 1.347-1.756 1.347-3.088 0-1.32-.474-2.395-1.293-3.159-.84-.78-2.003-1.242-3.272-1.242v-.55z" />
    </svg>
  );
}

export function TwitterIcon({ className = "size-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M23.643 4.937c-.835.37-1.732.62-2.675.733a4.67 4.67 0 0 0 2.048-2.578 9.3 9.3 0 0 1-2.958 1.13 4.66 4.66 0 0 0-7.938 4.25 13.229 13.229 0 0 1-9.602-4.868c-.4.69-.63 1.49-.63 2.342A4.66 4.66 0 0 0 3.96 9.824a4.647 4.647 0 0 1-2.11-.583v.06a4.66 4.66 0 0 0 3.737 4.568 4.692 4.692 0 0 1-2.104.08 4.661 4.661 0 0 0 4.352 3.234 9.348 9.348 0 0 1-5.786 1.995 9.5 9.5 0 0 1-1.112-.065 13.175 13.175 0 0 0 7.14 2.093c8.57 0 13.255-7.098 13.255-13.254 0-.2-.005-.402-.014-.602a9.47 9.47 0 0 0 2.323-2.41l.002-.003z" />
    </svg>
  );
}

export function MiYouSheIcon({ className = "size-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z" />
    </svg>
  );
}

export function GenericPlatformIcon({ platform, className = "size-4" }: { platform: string } & IconProps) {
  const letter = platform.charAt(0).toUpperCase();
  return (
    <span
      className={`flex items-center justify-center rounded-full bg-neutral-300 text-[8px] font-bold text-neutral-700 dark:bg-neutral-600 dark:text-neutral-200 ${className}`}
    >
      {letter}
    </span>
  );
}

export const PLATFORM_ICON_MAP: Record<string, React.ComponentType<IconProps>> = {
  pixiv: PixivIcon,
  twitter: TwitterIcon,
  miyoushe: MiYouSheIcon,
};

export const PLATFORM_COLORS: Record<string, string> = {
  pixiv: "text-[#0096fa] hover:text-[#0073cc]",
  twitter: "text-[#1da1f2] hover:text-[#0c85d0]",
  miyoushe: "text-[#00c3ff] hover:text-[#009dd4]",
};
