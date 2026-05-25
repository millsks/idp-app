/**
 * TanStack Query hook — authenticated library item list with filters.
 */
import { useQuery } from "@tanstack/react-query";
import { fetchLibraryItems, type LibraryFilters, type LibraryItemList } from "../api/library";
import { QUERY_KEYS } from "../api/queryKeys";

export function useLibraryItems(filters: LibraryFilters = {}) {
  return useQuery<LibraryItemList>({
    queryKey: QUERY_KEYS.libraryItems(filters),
    queryFn: () => fetchLibraryItems(filters),
  });
}
