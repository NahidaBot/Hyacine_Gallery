"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

export default function PanelDashboard() {
  const { slug } = useParams<{ slug: string }>();
  const base = `/panel/${slug}`;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Admin Dashboard</h1>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Link
          href={`${base}/artworks`}
          className="rounded-lg border border-neutral-200 p-6 transition-shadow hover:shadow-md dark:border-neutral-800"
        >
          <h2 className="mb-2 text-lg font-semibold">Artworks</h2>
          <p className="text-sm text-neutral-500">
            Browse, import, edit, and delete artworks
          </p>
        </Link>
        <Link
          href={`${base}/tags`}
          className="rounded-lg border border-neutral-200 p-6 transition-shadow hover:shadow-md dark:border-neutral-800"
        >
          <h2 className="mb-2 text-lg font-semibold">Tags</h2>
          <p className="text-sm text-neutral-500">
            Manage tags: create, rename, change type, delete
          </p>
        </Link>
      </div>
    </div>
  );
}
