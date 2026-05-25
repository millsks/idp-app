/**
 * TanStack Query key factory for the entire application.
 * Centralising keys prevents typos and makes cache invalidation predictable.
 */
import type { LibraryFilters } from "./library";

export const QUERY_KEYS = {
  /** Current authenticated user profile — GET /users/me */
  currentUser: () => ["users", "me"] as const,

  /** Public library items (no auth) — GET /library/items/public */
  libraryItemsPublic: () => ["library", "items", "public"] as const,

  /** Authenticated library items with filters — GET /library/items */
  libraryItems: (filters: LibraryFilters) => ["library", "items", filters] as const,

  /** Single library item detail — GET /library/items/:slug */
  libraryItem: (slug: string) => ["library", "item", slug] as const,
} as const;
