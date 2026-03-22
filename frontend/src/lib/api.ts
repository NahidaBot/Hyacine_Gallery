import type {
  Artwork,
  ArtworkListResponse,
  FriendLink,
  SemanticSearchResponse,
  TagListResponse,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchArtworks(params?: {
  page?: number;
  pageSize?: number;
  platform?: string;
  tag?: string;
  q?: string;
  authorId?: number;
  authorName?: string;
}): Promise<ArtworkListResponse> {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  if (params?.pageSize) sp.set("page_size", String(params.pageSize));
  if (params?.platform) sp.set("platform", params.platform);
  if (params?.tag) sp.set("tag", params.tag);
  if (params?.q) sp.set("q", params.q);
  if (params?.authorId) sp.set("author_id", String(params.authorId));
  if (params?.authorName) sp.set("author_name", params.authorName);

  const qs = sp.toString();
  return apiFetch<ArtworkListResponse>(`/api/artworks${qs ? `?${qs}` : ""}`);
}

export async function fetchArtwork(id: number): Promise<Artwork> {
  return apiFetch<Artwork>(`/api/artworks/${id}`);
}

export async function fetchRandomArtwork(): Promise<Artwork> {
  return apiFetch<Artwork>("/api/artworks/random");
}

export async function fetchTags(): Promise<TagListResponse> {
  return apiFetch<TagListResponse>("/api/tags");
}

export async function fetchSemanticSearch(
  q: string,
  topK: number = 10,
): Promise<SemanticSearchResponse> {
  const sp = new URLSearchParams({ q, top_k: String(topK) });
  return apiFetch<SemanticSearchResponse>(`/api/artworks/search?${sp}`);
}

export async function fetchLinks(): Promise<FriendLink[]> {
  return apiFetch<FriendLink[]>("/api/links");
}
