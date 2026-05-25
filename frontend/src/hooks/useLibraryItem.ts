/**
 * TanStack Query hook — single authenticated library item detail.
 */
import { useQuery } from "@tanstack/react-query";
import { fetchLibraryItem, type LibraryItemDetail } from "../api/library";
import { QUERY_KEYS } from "../api/queryKeys";

export function useLibraryItem(slug: string) {
  return useQuery<LibraryItemDetail>({
    queryKey: QUERY_KEYS.libraryItem(slug),
    queryFn: () => fetchLibraryItem(slug),
    enabled: Boolean(slug),
  });
}
