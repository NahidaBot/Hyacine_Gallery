"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import type { Artwork } from "@/types";
import {
  adminDeleteArtwork,
  adminFetchArtwork,
  adminUpdateArtwork,
} from "@/lib/admin-api";

export default function ArtworkEditPage() {
  const { slug, id } = useParams<{ slug: string; id: string }>();
  const router = useRouter();
  const base = `/panel/${slug}`;
  const artworkId = Number(id);

  const [artwork, setArtwork] = useState<Artwork | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Form state
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [isNsfw, setIsNsfw] = useState(false);
  const [isAi, setIsAi] = useState(false);
  const [tagsInput, setTagsInput] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminFetchArtwork(artworkId);
      setArtwork(data);
      setTitle(data.title);
      setAuthor(data.author);
      setIsNsfw(data.is_nsfw);
      setIsAi(data.is_ai);
      setTagsInput(data.tags.map((t) => t.name).join(", "));
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [artworkId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const tags = tagsInput
        .split(/[\s,]+/)
        .map((t) => t.replace(/^#/, "").trim())
        .filter(Boolean);
      const updated = await adminUpdateArtwork(artworkId, {
        title,
        author,
        is_nsfw: isNsfw,
        is_ai: isAi,
        tags,
      });
      setArtwork(updated);
      setTagsInput(updated.tags.map((t) => t.name).join(", "));
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete artwork #${artworkId}? This cannot be undone.`))
      return;
    try {
      await adminDeleteArtwork(artworkId);
      router.push(`${base}/artworks`);
    } catch (err) {
      alert(String(err));
    }
  }

  if (loading)
    return <p className="text-sm text-neutral-400">Loading...</p>;
  if (!artwork)
    return <p className="text-sm text-red-500">{error || "Not found"}</p>;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">
          Edit Artwork #{artwork.id}
        </h1>
        <button
          onClick={handleDelete}
          className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          Delete
        </button>
      </div>

      {/* Image preview */}
      <div className="mb-6 flex gap-2 overflow-x-auto">
        {artwork.images.map((img) => (
          <a
            key={img.id}
            href={img.url_original}
            target="_blank"
            rel="noopener noreferrer"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={img.url_thumb || img.url_original}
              alt={`page ${img.page_index + 1}`}
              className="h-32 rounded border border-neutral-200 object-cover dark:border-neutral-700"
            />
          </a>
        ))}
      </div>

      {/* Meta info */}
      <div className="mb-6 text-sm text-neutral-500">
        <span>{artwork.platform} / {artwork.pid}</span>
        {artwork.source_url && (
          <>
            {" · "}
            <a
              href={artwork.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
            >
              Source
            </a>
          </>
        )}
        <span> · {artwork.images.length} images</span>
      </div>

      {/* Edit form */}
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium">Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Author</label>
          <input
            type="text"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            className="w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">
            Tags (comma or space separated)
          </label>
          <input
            type="text"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            className="w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
        </div>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isNsfw}
              onChange={(e) => setIsNsfw(e.target.checked)}
            />
            NSFW
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isAi}
              onChange={(e) => setIsAi(e.target.checked)}
            />
            AI Generated
          </label>
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
          <button
            onClick={() => router.push(`${base}/artworks`)}
            className="rounded border border-neutral-300 px-6 py-2 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
          >
            Back
          </button>
        </div>
      </div>
    </div>
  );
}
