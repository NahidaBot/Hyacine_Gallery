"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { Artwork, ArtworkListResponse } from "@/types";
import {
  adminDeleteArtwork,
  adminFetchArtworks,
  adminImportArtwork,
} from "@/lib/admin-api";

export default function ArtworksPage() {
  const { slug } = useParams<{ slug: string }>();
  const base = `/panel/${slug}`;

  const [artworks, setArtworks] = useState<Artwork[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  // Import modal
  const [showImport, setShowImport] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const [importTags, setImportTags] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");

  const pageSize = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data: ArtworkListResponse = await adminFetchArtworks({
        page,
        pageSize,
        q: search || undefined,
      });
      setArtworks(data.data);
      setTotal(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDelete(id: number) {
    if (!confirm(`Delete artwork #${id}?`)) return;
    try {
      await adminDeleteArtwork(id);
      await load();
    } catch (err) {
      alert(String(err));
    }
  }

  async function handleImport() {
    if (!importUrl.trim()) return;
    setImporting(true);
    setImportError("");
    try {
      const tags = importTags
        .split(/[\s,]+/)
        .map((t) => t.replace(/^#/, "").trim())
        .filter(Boolean);
      await adminImportArtwork(importUrl.trim(), tags);
      setShowImport(false);
      setImportUrl("");
      setImportTags("");
      await load();
    } catch (err) {
      setImportError(String(err));
    } finally {
      setImporting(false);
    }
  }

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Artworks</h1>
        <button
          onClick={() => setShowImport(true)}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Import
        </button>
      </div>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search by title or author..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
      </div>

      {/* Import Modal */}
      {showImport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="mx-4 w-full max-w-md rounded-lg bg-white p-6 dark:bg-neutral-900">
            <h2 className="mb-4 text-lg font-bold">Import Artwork</h2>
            <label className="mb-1 block text-sm font-medium">URL</label>
            <input
              type="url"
              value={importUrl}
              onChange={(e) => setImportUrl(e.target.value)}
              placeholder="https://www.pixiv.net/artworks/..."
              className="mb-3 w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            />
            <label className="mb-1 block text-sm font-medium">
              Tags (space or comma separated)
            </label>
            <input
              type="text"
              value={importTags}
              onChange={(e) => setImportTags(e.target.value)}
              placeholder="landscape scenery"
              className="mb-4 w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800"
            />
            {importError && (
              <p className="mb-3 text-sm text-red-500">{importError}</p>
            )}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowImport(false)}
                className="rounded px-4 py-2 text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800"
              >
                Cancel
              </button>
              <button
                onClick={handleImport}
                disabled={importing}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {importing ? "Importing..." : "Import"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <p className="text-sm text-neutral-400">Loading...</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-neutral-200 text-xs uppercase text-neutral-500 dark:border-neutral-700">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Thumb</th>
                  <th className="px-3 py-2">Title</th>
                  <th className="px-3 py-2">Author</th>
                  <th className="px-3 py-2">Platform</th>
                  <th className="px-3 py-2">Tags</th>
                  <th className="px-3 py-2">Flags</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {artworks.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-neutral-100 dark:border-neutral-800"
                  >
                    <td className="px-3 py-2 tabular-nums">{a.id}</td>
                    <td className="px-3 py-2">
                      {a.images[0] ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={
                            a.images[0].url_thumb || a.images[0].url_original
                          }
                          alt=""
                          className="h-10 w-10 rounded object-cover"
                        />
                      ) : (
                        <span className="text-neutral-300">-</span>
                      )}
                    </td>
                    <td className="max-w-48 truncate px-3 py-2">
                      <Link
                        href={`${base}/artworks/${a.id}`}
                        className="hover:underline"
                      >
                        {a.title || a.pid}
                      </Link>
                    </td>
                    <td className="max-w-32 truncate px-3 py-2">{a.author}</td>
                    <td className="px-3 py-2">{a.platform}</td>
                    <td className="max-w-40 truncate px-3 py-2 text-xs text-neutral-500">
                      {a.tags.map((t) => `#${t.name}`).join(" ")}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {a.is_nsfw && (
                        <span className="mr-1 rounded bg-red-100 px-1.5 py-0.5 text-red-600 dark:bg-red-900/30">
                          NSFW
                        </span>
                      )}
                      {a.is_ai && (
                        <span className="rounded bg-purple-100 px-1.5 py-0.5 text-purple-600 dark:bg-purple-900/30">
                          AI
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        <Link
                          href={`${base}/artworks/${a.id}`}
                          className="text-blue-600 hover:underline"
                        >
                          Edit
                        </Link>
                        <button
                          onClick={() => handleDelete(a.id)}
                          className="text-red-500 hover:underline"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {artworks.length === 0 && (
                  <tr>
                    <td
                      colSpan={8}
                      className="px-3 py-8 text-center text-neutral-400"
                    >
                      No artworks found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between text-sm">
              <span className="text-neutral-500">
                Page {page} of {totalPages} ({total} total)
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="rounded border border-neutral-300 px-3 py-1 disabled:opacity-30 dark:border-neutral-700"
                >
                  Prev
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="rounded border border-neutral-300 px-3 py-1 disabled:opacity-30 dark:border-neutral-700"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
