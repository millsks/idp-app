/**
 * API functions for the Library endpoints.
 */
import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LibraryItem {
  slug: string;
  title: string;
  description: string;
  content_type: string;
  tags: string[];
  is_public: boolean;
  target_ai: string | null;
  author: string | null;
  last_updated: string | null;
}

export interface LibraryItemList {
  items: LibraryItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface LibraryFilters {
  type?: string;
  tags?: string[];
  target_ai?: string;
  q?: string;
  page?: number;
  size?: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * Fetch the public library preview (no auth required).
 * Used on the landing page and the unauthenticated library page.
 */
export async function fetchPublicLibraryItems(): Promise<LibraryItemList> {
  const response = await apiClient.get<LibraryItemList>("/library/items/public");
  return response.data;
}

/**
 * Fetch the full authenticated library item list with optional filters.
 * Requires a valid JWT (attached automatically by the Axios interceptor).
 */
export async function fetchLibraryItems(filters: LibraryFilters = {}): Promise<LibraryItemList> {
  const params: Record<string, string | number | string[]> = {};
  if (filters.type !== undefined) params.type = filters.type;
  if (filters.target_ai !== undefined) params.target_ai = filters.target_ai;
  if (filters.q !== undefined && filters.q !== "") params.q = filters.q;
  if (filters.page !== undefined) params.page = filters.page;
  if (filters.size !== undefined) params.size = filters.size;
  // FastAPI accepts repeated query param for list values
  if (filters.tags && filters.tags.length > 0) params.tags = filters.tags;

  const response = await apiClient.get<LibraryItemList>("/library/items", {
    params,
    // FastAPI expects repeated keys for arrays: ?tags=a&tags=b
    // Axios default would produce ?tags[]=a&tags[]=b — override here.
    paramsSerializer: (p: Record<string, string | number | string[]>) => {
      const search = new URLSearchParams();
      for (const [key, value] of Object.entries(p)) {
        if (Array.isArray(value)) {
          for (const item of value) {
            search.append(key, item);
          }
        } else {
          search.append(key, String(value));
        }
      }
      return search.toString();
    },
  });
  return response.data;
}
