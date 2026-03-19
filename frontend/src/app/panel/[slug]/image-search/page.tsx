"use client";

import { useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { SimilarArtworkInfo } from "@/types";
import { adminSearchByImage } from "@/lib/admin-api";

export default function ImageSearchPage() {
  const { slug } = useParams<{ slug: string }>();
  const base = `/panel/${slug}`;

  const fileRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [results, setResults] = useState<SimilarArtworkInfo[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [threshold, setThreshold] = useState(10);

  async function handleFile(file: File) {
    setPreview(URL.createObjectURL(file));
    setSearching(true);
    setError("");
    setResults([]);
    try {
      const data = await adminSearchByImage(file, threshold);
      setResults(data);
    } catch (err) {
      setError(String(err));
    } finally {
      setSearching(false);
    }
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  function onPaste(e: React.ClipboardEvent) {
    const file = e.clipboardData.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div onPaste={onPaste}>
      <h1 className="mb-2 text-2xl font-bold">Image Search</h1>
      <p className="mb-6 text-sm text-neutral-400">
        Upload an image to find similar artworks via perceptual hash.
      </p>

      {/* Threshold */}
      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm text-neutral-500">Threshold (0-20):</label>
        <input
          type="number"
          min={0}
          max={20}
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
          className="w-20 rounded border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
        <span className="text-xs text-neutral-400">Lower = stricter match</span>
      </div>

      {/* Upload area */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
        className="mb-6 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-neutral-300 p-8 transition-colors hover:border-blue-400 dark:border-neutral-700 dark:hover:border-blue-500"
      >
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          onChange={onFileChange}
          className="hidden"
        />
        {preview ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img src={preview} alt="Uploaded" className="max-h-48 rounded" />
        ) : (
          <>
            <p className="text-sm text-neutral-500">
              Click, drag & drop, or paste an image
            </p>
          </>
        )}
      </div>

      {/* Status */}
      {searching && <p className="mb-4 text-sm text-neutral-400">Searching...</p>}
      {error && <p className="mb-4 text-sm text-red-500">{error}</p>}

      {/* Results */}
      {!searching && results.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold">
            {results.length} match{results.length > 1 ? "es" : ""} found
          </h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
            {results.map((r) => (
              <Link
                key={r.artwork_id}
                href={`${base}/artworks/${r.artwork_id}`}
                className="overflow-hidden rounded-lg border border-neutral-200 transition-shadow hover:shadow-md dark:border-neutral-800"
              >
                {r.thumb_url && (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={r.thumb_url}
                    alt=""
                    className="w-full"
                  />
                )}
                <div className="p-2">
                  <p className="truncate text-sm font-medium">
                    #{r.artwork_id} — {r.title || r.pid}
                  </p>
                  <p className="text-xs text-neutral-500">
                    {r.platform}/{r.pid} · distance: {r.distance}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {!searching && !error && preview && results.length === 0 && (
        <p className="text-sm text-neutral-400">No similar artworks found.</p>
      )}
    </div>
  );
}
