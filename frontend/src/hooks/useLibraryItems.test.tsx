/**
 * Unit tests for useLibraryItems hook.
 * fetchLibraryItems is mocked so no real HTTP calls are made.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useLibraryItems } from "./useLibraryItems";
import type { LibraryItemList } from "../api/library";

vi.mock("../api/library", () => ({
  fetchLibraryItems: vi.fn(),
}));

import { fetchLibraryItems } from "../api/library";

const mockList: LibraryItemList = {
  items: [
    {
      slug: "my-skill",
      title: "My Skill",
      description: "A test skill",
      content_type: "Skill",
      tags: ["python"],
      is_public: true,
      target_ai: "Claude",
      author: "alice",
      last_updated: "2026-01-01",
    },
  ],
  total: 1,
  page: 1,
  size: 20,
  pages: 1,
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useLibraryItems", () => {
  it("returns data from fetchLibraryItems on success", async () => {
    vi.mocked(fetchLibraryItems).mockResolvedValueOnce(mockList);

    const { result } = renderHook(() => useLibraryItems(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(result.current.data).toEqual(mockList);
    expect(fetchLibraryItems).toHaveBeenCalledWith({});
  });

  it("passes filters to fetchLibraryItems", async () => {
    vi.mocked(fetchLibraryItems).mockResolvedValueOnce(mockList);
    const filters = { type: "Skill", q: "test" };

    const { result } = renderHook(() => useLibraryItems(filters), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(fetchLibraryItems).toHaveBeenCalledWith(filters);
  });

  it("exposes isLoading true initially", () => {
    vi.mocked(fetchLibraryItems).mockReturnValue(
      new Promise(() => {
        /* never resolves */
      }),
    );

    const { result } = renderHook(() => useLibraryItems(), { wrapper });

    expect(result.current.isLoading).toBe(true);
  });
});
