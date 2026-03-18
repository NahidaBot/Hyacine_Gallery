import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hyacine Gallery",
  description: "Image gallery with multi-platform support",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="font-sans antialiased">
        <header className="border-b border-neutral-200 dark:border-neutral-800">
          <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <a href="/" className="text-xl font-bold">
              Hyacine Gallery
            </a>
            <div className="flex gap-6 text-sm">
              <a href="/" className="hover:underline">
                Gallery
              </a>
              <a href="/tags" className="hover:underline">
                Tags
              </a>
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
