import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getToken,
  saveToken,
  clearToken,
  loginWithTelegram,
  fetchMe,
  fetchAuthConfig,
  adminFetchArtworks,
  adminFetchArtwork,
  adminDeleteArtwork,
  adminUpdateArtwork,
  adminDeleteArtworkImage,
  adminImportArtwork,
  adminAddSource,
  adminDeleteSource,
  adminMergeArtwork,
  adminFetchTags,
  adminCreateTag,
  adminUpdateTag,
  adminDeleteTag,
  adminFetchBotChannels,
  adminCreateBotChannel,
  adminUpdateBotChannel,
  adminDeleteBotChannel,
  adminFetchBotSettings,
  adminUpdateBotSettings,
  adminFetchTagTypes,
  adminCreateTagType,
  adminUpdateTagType,
  adminDeleteTagType,
  adminFetchUsers,
  adminCreateUser,
  adminUpdateUser,
  adminDeleteUser,
  adminFetchUserCredentials,
  adminDeleteUserCredential,
  adminFetchAuthors,
  adminUpdateAuthor,
  adminDeleteAuthor,
  adminFetchLinks,
  adminCreateLink,
  adminUpdateLink,
  adminDeleteLink,
  adminFetchPostLogs,
} from "../admin-api";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Mock localStorage
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

describe("token management", () => {
  it("saveToken and getToken", () => {
    saveToken("test-jwt");
    expect(getToken()).toBe("test-jwt");
  });

  it("clearToken", () => {
    saveToken("test-jwt");
    clearToken();
    expect(getToken()).toBe("");
  });
});

describe("loginWithTelegram", () => {
  it("POST /api/auth/telegram", async () => {
    mockOk({ access_token: "jwt", role: "owner" });
    const result = await loginWithTelegram({
      id: 1,
      first_name: "Test",
      auth_date: 123,
      hash: "abc",
    });
    expect(result.access_token).toBe("jwt");
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/auth/telegram");
    expect(init.method).toBe("POST");
  });

  it("throws on error", async () => {
    mockError(401);
    await expect(
      loginWithTelegram({ id: 1, first_name: "T", auth_date: 1, hash: "x" }),
    ).rejects.toThrow();
  });
});

describe("fetchMe", () => {
  it("GET /api/auth/me with Bearer token", async () => {
    saveToken("mytoken");
    mockOk({ id: 1, tg_id: 123, tg_username: "user", role: "owner" });
    await fetchMe();
    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer mytoken");
  });
});

describe("fetchAuthConfig", () => {
  it("GET /api/auth/config", async () => {
    mockOk({ bot_username: "mybot" });
    const result = await fetchAuthConfig();
    expect(result.bot_username).toBe("mybot");
  });
});

describe("artwork admin APIs", () => {
  it("adminFetchArtworks with filters", async () => {
    mockOk({ data: [], total: 0, page: 1, page_size: 20 });
    await adminFetchArtworks({ platform: "pixiv", q: "test" });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("platform=pixiv");
    expect(url).toContain("q=test");
  });

  it("adminFetchArtwork", async () => {
    mockOk({ id: 1 });
    await adminFetchArtwork(1);
    expect(mockFetch.mock.calls[0][0]).toContain("/api/artworks/1");
  });

  it("adminDeleteArtwork", async () => {
    mockOk({ detail: "ok" });
    await adminDeleteArtwork(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/admin/artworks/1");
    expect(init.method).toBe("DELETE");
  });

  it("adminUpdateArtwork", async () => {
    mockOk({ id: 1, title: "New" });
    await adminUpdateArtwork(1, { title: "New" });
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/admin/artworks/1");
    expect(init.method).toBe("PUT");
  });

  it("adminDeleteArtworkImage", async () => {
    mockOk({ detail: "ok" });
    await adminDeleteArtworkImage(1, 2);
    expect(mockFetch.mock.calls[0][0]).toContain(
      "/api/admin/artworks/1/images/2",
    );
  });

  it("adminImportArtwork", async () => {
    mockOk({ artwork: { id: 1 }, similar: [] });
    await adminImportArtwork("https://pixiv.net/artworks/123", ["tag1"], true);
    const [, init] = mockFetch.mock.calls[0];
    const body = JSON.parse(init.body);
    expect(body.url).toBe("https://pixiv.net/artworks/123");
    expect(body.tags).toEqual(["tag1"]);
    expect(body.auto_merge).toBe(true);
  });

  it("adminAddSource", async () => {
    mockOk({ id: 1 });
    await adminAddSource(1, "https://example.com");
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/admin/artworks/1/sources");
    expect(init.method).toBe("POST");
  });

  it("adminDeleteSource", async () => {
    mockOk({ detail: "ok" });
    await adminDeleteSource(1, 2);
    expect(mockFetch.mock.calls[0][0]).toContain(
      "/api/admin/artworks/1/sources/2",
    );
  });

  it("adminMergeArtwork", async () => {
    mockOk({ id: 1 });
    await adminMergeArtwork(1, 2);
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.source_artwork_id).toBe(2);
  });
});

describe("tag admin APIs", () => {
  it("adminFetchTags with type filter", async () => {
    mockOk({ data: [], total: 0 });
    await adminFetchTags("character");
    expect(mockFetch.mock.calls[0][0]).toContain("type=character");
  });

  it("adminCreateTag", async () => {
    mockOk({ id: 1, name: "test" });
    await adminCreateTag({ name: "test", type: "general" });
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/admin/tags");
    expect(init.method).toBe("POST");
  });

  it("adminUpdateTag", async () => {
    mockOk({ id: 1, name: "updated" });
    await adminUpdateTag(1, { name: "updated" });
    expect(mockFetch.mock.calls[0][1].method).toBe("PUT");
  });

  it("adminDeleteTag", async () => {
    mockOk({ detail: "ok" });
    await adminDeleteTag(1);
    expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
  });
});

describe("tag type admin APIs", () => {
  it("adminFetchTagTypes", async () => {
    mockOk([]);
    await adminFetchTagTypes();
    expect(mockFetch.mock.calls[0][0]).toContain("/api/tags/types");
  });

  it("adminCreateTagType", async () => {
    mockOk({ id: 1, name: "custom" });
    await adminCreateTagType({ name: "custom" });
    expect(mockFetch.mock.calls[0][0]).toContain("/api/admin/tag-types");
  });

  it("adminUpdateTagType", async () => {
    mockOk({ id: 1, name: "updated" });
    await adminUpdateTagType(1, { label: "Updated" });
    expect(mockFetch.mock.calls[0][0]).toContain("/api/admin/tag-types/1");
  });

  it("adminDeleteTagType", async () => {
    mockOk({});
    await adminDeleteTagType(1);
    expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
  });
});

describe("bot channel APIs", () => {
  it("adminFetchBotChannels", async () => {
    mockOk([]);
    await adminFetchBotChannels("telegram");
    expect(mockFetch.mock.calls[0][0]).toContain(
      "/api/admin/bot/channels?platform=telegram",
    );
  });

  it("adminCreateBotChannel", async () => {
    mockOk({ id: 1 });
    await adminCreateBotChannel({ channel_id: "-100123" });
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });

  it("adminUpdateBotChannel", async () => {
    mockOk({ id: 1 });
    await adminUpdateBotChannel(1, { name: "Updated" });
    expect(mockFetch.mock.calls[0][0]).toContain("/api/admin/bot/channels/1");
  });

  it("adminDeleteBotChannel", async () => {
    mockOk({});
    await adminDeleteBotChannel(1);
    expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
  });
});

describe("bot settings APIs", () => {
  it("adminFetchBotSettings", async () => {
    mockOk([]);
    await adminFetchBotSettings();
    expect(mockFetch.mock.calls[0][0]).toContain("/api/admin/bot/settings");
  });

  it("adminUpdateBotSettings", async () => {
    mockOk({});
    await adminUpdateBotSettings({ key: "value" });
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.settings).toEqual({ key: "value" });
  });
});

describe("user admin APIs", () => {
  it("adminFetchUsers", async () => {
    mockOk([]);
    await adminFetchUsers();
    expect(mockFetch.mock.calls[0][0]).toContain("/api/admin/users");
  });

  it("adminCreateUser", async () => {
    mockOk({ id: 1 });
    await adminCreateUser({ tg_username: "test" });
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });

  it("adminUpdateUser", async () => {
    mockOk({ id: 1 });
    await adminUpdateUser(1, { role: "admin" });
    expect(mockFetch.mock.calls[0][0]).toContain("/api/admin/users/1");
  });

  it("adminDeleteUser", async () => {
    mockOk({});
    await adminDeleteUser(1);
    expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
  });

  it("adminFetchUserCredentials", async () => {
    mockOk([]);
    await adminFetchUserCredentials(1);
    expect(mockFetch.mock.calls[0][0]).toContain(
      "/api/admin/users/1/credentials",
    );
  });

  it("adminDeleteUserCredential", async () => {
    mockOk({});
    await adminDeleteUserCredential(1, 2);
    expect(mockFetch.mock.calls[0][0]).toContain(
      "/api/admin/users/1/credentials/2",
    );
  });
});

describe("author admin APIs", () => {
  it("adminFetchAuthors with platform", async () => {
    mockOk([]);
    await adminFetchAuthors("pixiv");
    expect(mockFetch.mock.calls[0][0]).toContain("platform=pixiv");
  });

  it("adminUpdateAuthor", async () => {
    mockOk({ id: 1 });
    await adminUpdateAuthor(1, { name: "New" });
    expect(mockFetch.mock.calls[0][0]).toContain("/api/admin/authors/1");
  });

  it("adminDeleteAuthor", async () => {
    mockOk({});
    await adminDeleteAuthor(1);
    expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
  });
});

describe("link admin APIs", () => {
  it("adminFetchLinks", async () => {
    mockOk([]);
    await adminFetchLinks();
    expect(mockFetch.mock.calls[0][0]).toContain("/api/admin/links");
  });

  it("adminCreateLink", async () => {
    mockOk({ id: 1 });
    await adminCreateLink({ name: "Test", url: "https://example.com" });
    expect(mockFetch.mock.calls[0][1].method).toBe("POST");
  });

  it("adminUpdateLink", async () => {
    mockOk({ id: 1 });
    await adminUpdateLink(1, { name: "Updated" });
    expect(mockFetch.mock.calls[0][0]).toContain("/api/admin/links/1");
  });

  it("adminDeleteLink", async () => {
    mockOk({});
    await adminDeleteLink(1);
    expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
  });
});

describe("post logs API", () => {
  it("adminFetchPostLogs with filters", async () => {
    mockOk({ data: [], total: 0, page: 1, page_size: 20 });
    await adminFetchPostLogs({ artwork_id: 1, page: 2 });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("artwork_id=1");
    expect(url).toContain("page=2");
  });
});

describe("adminFetch error handling", () => {
  it("throws with error text", async () => {
    mockError(403);
    await expect(adminFetchArtwork(1)).rejects.toThrow();
  });
});
