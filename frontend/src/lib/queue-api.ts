import { getToken } from "./admin-api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export interface QueueItem {
  id: number;
  artwork_id: number;
  platform: string;
  channel_id: string;
  priority: number;
  status: string;
  added_by: string;
  error: string;
  created_at: string;
  processed_at: string | null;
}

export interface QueueListResponse {
  data: QueueItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface NextTimesResponse {
  times: string[];
  interval_minutes: number;
  pending_count: number;
}

export interface BotSetting {
  key: string;
  value: string;
  description: string;
}

export async function fetchQueue(
  status = "pending",
  page = 1,
  pageSize = 50,
): Promise<QueueListResponse> {
  return apiFetch<QueueListResponse>(
    `/api/admin/bot/queue?status=${status}&page=${page}&page_size=${pageSize}`,
  );
}

export async function addToQueue(
  artworkId: number,
  priority = 100,
): Promise<QueueItem> {
  return apiFetch<QueueItem>("/api/admin/bot/queue", {
    method: "POST",
    body: JSON.stringify({ artwork_id: artworkId, priority }),
  });
}

export async function deleteQueueItem(itemId: number): Promise<void> {
  await apiFetch<unknown>(`/api/admin/bot/queue/${itemId}`, {
    method: "DELETE",
  });
}

export async function updateQueuePriority(
  itemId: number,
  priority: number,
): Promise<QueueItem> {
  return apiFetch<QueueItem>(`/api/admin/bot/queue/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify({ priority }),
  });
}

export async function fetchNextTimes(
  count = 5,
): Promise<NextTimesResponse> {
  return apiFetch<NextTimesResponse>(
    `/api/admin/bot/queue/next-times?count=${count}`,
  );
}

export async function fetchBotSettings(): Promise<BotSetting[]> {
  return apiFetch<BotSetting[]>("/api/admin/bot/settings");
}

export async function saveBotSettings(
  settings: Record<string, string>,
): Promise<void> {
  await apiFetch<unknown>("/api/admin/bot/settings", {
    method: "PUT",
    body: JSON.stringify({ settings }),
  });
}
