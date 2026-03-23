import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchArtworks,
  fetchArtwork,
  fetchRandomArtwork,
  fetchTags,
  fetchSemanticSearch,
  fetchAuthorByName,
  fetchAuthorArtworks,
  fetchLinks,
} from "../api";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function mockOk(data: unknown) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(data),
  });
}

function mockError(status = 500) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    statusText: "Error",
  });
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("fetchArtworks", () => {
  it("calls /api/artworks without params", async () => {
    mockOk({ data: [], total: 0, page: 1, page_size: 20 });
    const result = await fetchArtworks();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/artworks"),
      expect.any(Object),
    );
    expect(result.total).toBe(0);
  });

  it("includes filter params in URL", async () => {
    mockOk({ data: [], total: 0, page: 1, page_size: 20 });
    await fetchArtworks({
      page: 2,
      pageSize: 10,
      platform: "pixiv",
      tag: "landscape",
      q: "test",
    });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("page=2");
    expect(url).toContain("page_size=10");
    expect(url).toContain("platform=pixiv");
    expect(url).toContain("tag=landscape");
    expect(url).toContain("q=test");
  });

  it("includes author params", async () => {
    mockOk({ data: [], total: 0, page: 1, page_size: 20 });
    await fetchArtworks({ authorId: 5, authorName: "Artist" });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("author_id=5");
    expect(url).toContain("author_name=Artist");
  });
});

describe("fetchArtwork", () => {
  it("calls /api/artworks/{id}", async () => {
    mockOk({ id: 1, platform: "pixiv" });
    const result = await fetchArtwork(1);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/artworks/1"),
      expect.any(Object),
    );
    expect(result.id).toBe(1);
  });
});

describe("fetchRandomArtwork", () => {
  it("calls /api/artworks/random", async () => {
    mockOk({ id: 42 });
    await fetchRandomArtwork();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/artworks/random"),
      expect.any(Object),
    );
  });
});

describe("fetchTags", () => {
  it("calls /api/tags", async () => {
    mockOk({ data: [], total: 0 });
    await fetchTags();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/tags"),
      expect.any(Object),
    );
  });
});

describe("fetchSemanticSearch", () => {
  it("calls /api/artworks/search with params", async () => {
    mockOk({ results: [], query: "test" });
    await fetchSemanticSearch("test", 5);
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("/api/artworks/search");
    expect(url).toContain("q=test");
    expect(url).toContain("top_k=5");
  });
});

describe("fetchAuthorByName", () => {
  it("encodes name in URL", async () => {
    mockOk({ id: 1, name: "Test Artist" });
    await fetchAuthorByName("Test Artist");
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("/api/authors/by-name/Test%20Artist");
  });
});

describe("fetchAuthorArtworks", () => {
  it("calls /api/authors/{id}/artworks with pagination", async () => {
    mockOk({ data: [], total: 0, page: 2, page_size: 10 });
    await fetchAuthorArtworks(1, { page: 2, pageSize: 10 });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("/api/authors/1/artworks");
    expect(url).toContain("page=2");
  });
});

describe("fetchLinks", () => {
  it("calls /api/links", async () => {
    mockOk([]);
    await fetchLinks();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/links"),
      expect.any(Object),
    );
  });
});

describe("apiFetch error handling", () => {
  it("throws on non-ok response", async () => {
    mockError(404);
    await expect(fetchArtwork(999)).rejects.toThrow("API error");
  });
});
