import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchQueue,
  addToQueue,
  deleteQueueItem,
  updateQueuePriority,
  fetchNextTimes,
  fetchBotSettings,
  saveBotSettings,
} from "../queue-api";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Mock localStorage for getToken dependency
const store: Record<string, string> = {};
vi.stubGlobal("localStorage", {
  getItem: (key: string) => store[key] ?? null,
  setItem: (key: string, val: string) => {
    store[key] = val;
  },
  removeItem: (key: string) => {
    delete store[key];
  },
});

function mockOk(data: unknown) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
}

function mockError(status = 500) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    statusText: "Error",
    text: () => Promise.resolve("Error"),
  });
}

beforeEach(() => {
  mockFetch.mockReset();
  Object.keys(store).forEach((k) => delete store[k]);
});

describe("fetchQueue", () => {
  it("GET /api/admin/bot/queue with params", async () => {
    mockOk({ data: [], total: 0, page: 1, page_size: 50 });
    await fetchQueue("pending", 1, 50);
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("/api/admin/bot/queue");
    expect(url).toContain("status=pending");
    expect(url).toContain("page=1");
    expect(url).toContain("page_size=50");
  });
});

describe("addToQueue", () => {
  it("POST /api/admin/bot/queue", async () => {
    mockOk({ id: 1, artwork_id: 5, priority: 50 });
    const result = await addToQueue(5, 50);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/admin/bot/queue");
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body);
    expect(body.artwork_id).toBe(5);
    expect(body.priority).toBe(50);
    expect(result.id).toBe(1);
  });
});

describe("deleteQueueItem", () => {
  it("DELETE /api/admin/bot/queue/{id}", async () => {
    mockOk({ detail: "ok" });
    await deleteQueueItem(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/admin/bot/queue/1");
    expect(init.method).toBe("DELETE");
  });
});

describe("updateQueuePriority", () => {
  it("PATCH /api/admin/bot/queue/{id}", async () => {
    mockOk({ id: 1, priority: 10 });
    const result = await updateQueuePriority(1, 10);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/admin/bot/queue/1");
    expect(init.method).toBe("PATCH");
    expect(result.priority).toBe(10);
  });
});

describe("fetchNextTimes", () => {
  it("GET /api/admin/bot/queue/next-times", async () => {
    mockOk({ times: [], interval_minutes: 120, pending_count: 0 });
    await fetchNextTimes(3);
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("/api/admin/bot/queue/next-times");
    expect(url).toContain("count=3");
  });
});

describe("fetchBotSettings", () => {
  it("GET /api/admin/bot/settings", async () => {
    mockOk([{ key: "k", value: "v", description: "" }]);
    const result = await fetchBotSettings();
    expect(result).toHaveLength(1);
  });
});

describe("saveBotSettings", () => {
  it("PUT /api/admin/bot/settings", async () => {
    mockOk({});
    await saveBotSettings({ queue_enabled: "true" });
    const [, init] = mockFetch.mock.calls[0];
    expect(init.method).toBe("PUT");
    const body = JSON.parse(init.body);
    expect(body.settings.queue_enabled).toBe("true");
  });
});

describe("error handling", () => {
  it("throws on non-ok response", async () => {
    mockError(403);
    await expect(fetchQueue()).rejects.toThrow();
  });
});
