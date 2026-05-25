/**
 * TanStack Query key factory for the entire application.
 * Centralising keys prevents typos and makes cache invalidation predictable.
 */
export const QUERY_KEYS = {
  /** Current authenticated user profile — GET /users/me */
  currentUser: () => ["users", "me"] as const,
} as const;
