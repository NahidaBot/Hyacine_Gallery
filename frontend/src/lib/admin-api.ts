import type { Artwork, ArtworkListResponse, Tag, TagListResponse } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("admin_token") ?? "";
}

async function adminFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": getToken(),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ── Artworks ──

export async function adminFetchArtworks(params?: {
  page?: number;
  pageSize?: number;
  platform?: string;
  tag?: string;
  q?: string;
}): Promise<ArtworkListResponse> {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  if (params?.pageSize) sp.set("page_size", String(params.pageSize));
  if (params?.platform) sp.set("platform", params.platform);
  if (params?.tag) sp.set("tag", params.tag);
  if (params?.q) sp.set("q", params.q);
  const qs = sp.toString();
  return adminFetch<ArtworkListResponse>(`/api/artworks${qs ? `?${qs}` : ""}`);
}

export async function adminFetchArtwork(id: number): Promise<Artwork> {
  return adminFetch<Artwork>(`/api/artworks/${id}`);
}

export async function adminDeleteArtwork(id: number): Promise<void> {
  await adminFetch<unknown>(`/api/admin/artworks/${id}`, { method: "DELETE" });
}

export async function adminUpdateArtwork(
  id: number,
  data: {
    title?: string;
    author?: string;
    is_nsfw?: boolean;
    is_ai?: boolean;
    tags?: string[];
  },
): Promise<Artwork> {
  return adminFetch<Artwork>(`/api/admin/artworks/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function adminImportArtwork(
  url: string,
  tags?: string[],
): Promise<Artwork> {
  return adminFetch<Artwork>("/api/admin/artworks/import", {
    method: "POST",
    body: JSON.stringify({ url, tags: tags ?? [] }),
  });
}

// ── Tags ──

export async function adminFetchTags(type?: string): Promise<TagListResponse> {
  const qs = type ? `?type=${encodeURIComponent(type)}` : "";
  return adminFetch<TagListResponse>(`/api/tags${qs}`);
}

export async function adminCreateTag(data: {
  name: string;
  type?: string;
}): Promise<Tag> {
  return adminFetch<Tag>("/api/admin/tags", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminUpdateTag(
  id: number,
  data: { name?: string; type?: string; alias_of_id?: number | null },
): Promise<Tag> {
  return adminFetch<Tag>(`/api/admin/tags/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function adminDeleteTag(id: number): Promise<void> {
  await adminFetch<unknown>(`/api/admin/tags/${id}`, { method: "DELETE" });
}
