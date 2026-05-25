/**
 * Unit tests for library API wrapper functions.
 * apiClient is mocked so no real HTTP calls are made.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "./client";
import { fetchPublicLibraryItems, fetchLibraryItems, type LibraryItemList } from "./library";

vi.mock("./client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

const mockList: LibraryItemList = {
  items: [],
  total: 0,
  page: 1,
  size: 20,
  pages: 0,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("fetchPublicLibraryItems", () => {
  it("calls GET /library/items/public and returns the list", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockList });

    const result = await fetchPublicLibraryItems();

    expect(apiClient.get).toHaveBeenCalledWith("/library/items/public");
    expect(result).toEqual(mockList);
  });
});

describe("fetchLibraryItems", () => {
  it("calls GET /library/items with no params when called with empty filters", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockList });

    const result = await fetchLibraryItems();

    expect(apiClient.get).toHaveBeenCalledWith(
      "/library/items",
      expect.objectContaining({ params: {} }),
    );
    expect(result).toEqual(mockList);
  });

  it("passes type, target_ai, q, page, size as params", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockList });

    await fetchLibraryItems({ type: "Skill", target_ai: "Claude", q: "test", page: 2, size: 10 });

    const [, config] = vi.mocked(apiClient.get).mock.calls[0];
    expect((config as { params: Record<string, unknown> }).params).toEqual({
      type: "Skill",
      target_ai: "Claude",
      q: "test",
      page: 2,
      size: 10,
    });
  });

  it("omits q when q is an empty string", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockList });

    await fetchLibraryItems({ q: "" });

    const [, config] = vi.mocked(apiClient.get).mock.calls[0];
    expect((config as { params: Record<string, unknown> }).params).not.toHaveProperty("q");
  });

  it("passes tags array when tags are provided", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockList });

    await fetchLibraryItems({ tags: ["python", "llm"] });

    const [, config] = vi.mocked(apiClient.get).mock.calls[0];
    expect((config as { params: Record<string, unknown> }).params).toMatchObject({
      tags: ["python", "llm"],
    });
  });

  it("omits tags when the array is empty", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockList });

    await fetchLibraryItems({ tags: [] });

    const [, config] = vi.mocked(apiClient.get).mock.calls[0];
    expect((config as { params: Record<string, unknown> }).params).not.toHaveProperty("tags");
  });

  it("paramsSerializer produces repeated keys for tags array", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockList });

    await fetchLibraryItems({ tags: ["python", "llm"] });

    const [, config] = vi.mocked(apiClient.get).mock.calls[0];
    const serialize = (config as { paramsSerializer: (p: Record<string, unknown>) => string })
      .paramsSerializer;
    const serialized = serialize({ tags: ["python", "llm"] });
    expect(serialized).toBe("tags=python&tags=llm");
  });
});
