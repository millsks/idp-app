# Story 4.2: Library Browse, Search & Filter

Status: done

## Story

As an authenticated developer,
I want to browse, search, and filter the library of skills and prompts,
so that I can quickly find the content most relevant to my current task.

## Acceptance Criteria

1. Authenticated users navigating to `/library` see a list/grid of library items loaded from `GET /api/v1/library/items`.
2. Each library card displays: title, description snippet, `content_type` badge (Skill / Prompt), tags, and target AI assistant chips.
3. The library page first contentful paint completes in under 2 seconds.
4. Typing a search term in the search box filters results to items where the term matches title, description, tags, or content; results return within 500ms for up to 1,000 items.
5. If no results match, a "No results found" empty state message is shown.
6. A `content_type` filter (All / Skill / Prompt) narrows results to the selected type.
7. A `target_ai` filter narrows results to items targeting the selected AI assistant.
8. A tags filter narrows results to items with the selected tag.
9. Combined filters (type + target_ai + tags + search) apply AND logic — results satisfy all active filters simultaneously.
10. `GET /api/v1/library/items` with a valid JWT returns the standard envelope `{items, total, page, size, pages}` and supports query params: `?type=`, `?tags=`, `?target_ai=`, `?q=`, `?page=`, `?size=`.
11. `GET /api/v1/library/items` without a JWT returns HTTP 401.
12. Search and filtering are performed server-side (in the API) by reading from Redis cache — no full-text index service required for MVP1.
13. The library page is wrapped in `<ProtectedRoute>` — unauthenticated users are redirected to `/login`.

## Tasks / Subtasks

- [ ] Backend: Add `GET /api/v1/library/items` endpoint to `api/v1/routes/library.py` (AC: 10, 11, 12)
  - [ ] Requires `Annotated[User, Depends(get_current_user)]`
  - [ ] Query params: `type: str | None`, `tags: list[str] | None`, `target_ai: str | None`, `q: str | None`, `page: int = 1`, `size: int = 20`
  - [ ] Reads all slugs from `library:items` Redis Set, fetches each `library:item:{slug}` Hash
  - [ ] Applies filters in-memory: type match, tag intersection, target_ai match, full-text `q` across title+description+tags+content fields
  - [ ] Returns paginated results using standard envelope schema
  - [ ] Returns empty list (not 500) when `library:items` is empty
- [ ] Backend: Add `LibraryItemList` and `LibraryFilters` schemas to `schemas/library.py` (AC: 10)
  - [ ] `LibraryItem` (list version — no `content` field): `slug`, `title`, `description`, `content_type`, `tags`, `is_public`, `target_ai`, `author`, `last_updated`
  - [ ] `LibraryItemList`: `{items: list[LibraryItem], total, page, size, pages}`
- [ ] Backend: Write tests for library list endpoint in `tests/test_library.py` (AC: 10–12)
  - [ ] Test with mock Redis data
  - [ ] Test all filter combinations
  - [ ] Test pagination
  - [ ] Test 401 without auth
- [ ] Frontend: Create `frontend/src/api/library.ts` — typed API functions (AC: 1)
  - [ ] `fetchLibraryItems(filters: LibraryFilters): Promise<LibraryItemList>`
  - [ ] `fetchPublicLibraryItems(): Promise<LibraryItemList>` (reuse from Story 1.2 if created there)
- [ ] Frontend: Add library query keys to `api/queryKeys.ts` (AC: 1)
  - [ ] `QUERY_KEYS.libraryItems = (filters) => ['library', 'items', filters]`
- [ ] Frontend: Create `frontend/src/hooks/useLibraryItems.ts` — TanStack Query hook (AC: 1, 4)
  - [ ] `useQuery(QUERY_KEYS.libraryItems(filters), () => fetchLibraryItems(filters))`
- [ ] Frontend: Create `frontend/src/components/LibraryItem/SkillCard.tsx` (AC: 2)
  - [ ] MUI Card: title, description snippet (truncated), `content_type` chip, tags chips, target AI chips
  - [ ] Write `SkillCard.test.tsx`
- [ ] Frontend: Create `frontend/src/pages/LibraryPage.tsx` (AC: 1–9, 13)
  - [ ] Search input (debounced, 300ms) — updates `q` filter
  - [ ] `content_type` toggle buttons (All / Skill / Prompt)
  - [ ] `target_ai` multi-select or chip filter
  - [ ] Tags filter
  - [ ] Grid of `<SkillCard>` components from `useLibraryItems(filters)`
  - [ ] "No results found" empty state
  - [ ] Loading skeleton while query is pending
- [ ] Frontend: Register `/library` route in `App.tsx` under `<ProtectedRoute>` (AC: 13)
- [ ] Frontend: Write `LibraryPage.test.tsx`

## Dev Notes

- **Server-side filtering from Redis:** All library items are loaded from Redis into memory on each request (for up to 1,000 items this is acceptable per NFR-4.2.3). The filter/search logic runs in Python on the fetched list. This is deliberate — no Elasticsearch or full-text DB index is needed for MVP1.
- **Performance:** To meet the 500ms search budget, the Redis fetch should use a single pipeline to get all item hashes in one round-trip. Use `redis.pipeline()` → `HGETALL library:item:{slug}` for each slug → `execute()`.
- **Content in list view:** The `LibraryItem` list schema intentionally omits the `content` field (full Markdown). Content is only returned by the detail endpoint (Story 4.3). This keeps the list response size manageable.
- **Tags deserialization:** Tags stored in Redis as JSON strings — deserialize with `json.loads()` before filtering/returning.
- **Debounced search input:** Use a 300ms debounce on the frontend search input before updating the TanStack Query filter key. This prevents excessive API calls while typing.
- **Pagination:** Default `size=20`. The standard envelope `pages` count is `math.ceil(total / size)`.
- **Filter state management:** Keep filter state in `useState` in `LibraryPage` and pass as the TanStack Query key — this triggers refetch when filters change.

### Project Structure Notes

- Modify: `backend/src/idp_app/api/v1/routes/library.py` — add authenticated list endpoint
- Modify: `backend/src/idp_app/schemas/library.py` — add/update schemas
- Create: `frontend/src/api/library.ts`
- Modify: `frontend/src/api/queryKeys.ts`
- Create: `frontend/src/hooks/useLibraryItems.ts`
- Create: `frontend/src/components/LibraryItem/SkillCard.tsx`
- Create: `frontend/src/components/LibraryItem/SkillCard.test.tsx`
- Create: `frontend/src/pages/LibraryPage.tsx`
- Create: `frontend/src/pages/LibraryPage.test.tsx`
- Modify: `frontend/src/App.tsx` — add `/library` route under `<ProtectedRoute>`
- Modify: `backend/tests/test_library.py`

### References

- Architecture Section 2.3: Redis cache key schema [Source: _bmad-output/planning-artifacts/architecture.md#23-github-content-service-architecture]
- Architecture Section 2.5: API Surface [Source: _bmad-output/planning-artifacts/architecture.md#25-api-surface]
- Architecture ARCH-12: Standard response envelope [Source: _bmad-output/planning-artifacts/architecture.md]
- PRD FR-5.1, FR-5.2, FR-5.6 – FR-5.8, NFR-4.2.1, NFR-4.2.3 [Source: _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

### Review Findings

- [x] [Review][Decision] Pagination hardcoded to `page: 1` / `size: 50` — resolved: add pagination UI (MUI Pagination). Fixed: `size` reset to 20, `currentPage` state wired to filters and Pagination component.
- [x] [Review][Patch] `type` parameter shadows Python built-in — renamed to `content_type` with `Query(alias="type")` to preserve API contract [backend/src/idp_app/api/v1/routes/library.py]
- [x] [Review][Patch] Redis errors silently return HTTP 200 with empty list — both `smembers` and pipeline `execute` now raise HTTP 503 on exception [backend/src/idp_app/api/v1/routes/library.py]
- [x] [Review][Patch] `q` search excludes `content` field — `slug_to_content` dict now carries raw content through the pipeline loop; searchable string includes content [backend/src/idp_app/api/v1/routes/library.py]
- [x] [Review][Patch] Axios `tags` array serialization broken — added explicit `paramsSerializer` using URLSearchParams with `append` to produce repeated keys [frontend/src/api/library.ts]
- [x] [Review][Patch] Tag / targetAi filter options derived from filtered+paginated result set — separate `CATALOGUE_FILTERS` stable query (`size: 100`) for option lists; `allTags` / `targetAiOptions` derived from `catalogueData` [frontend/src/pages/LibraryPage.tsx]
- [x] [Review][Patch] Orphaned slug logging missing — added `logger.warning` for empty hash results and skips `_decode_item` call for empty `raw` [backend/src/idp_app/api/v1/routes/library.py]
- [x] [Review][Defer] Full dataset loaded into memory before filtering — all items fetched then filtered in Python; acknowledged as acceptable in Dev Notes for MVP1 (≤1,000 items) [backend/src/idp_app/api/v1/routes/library.py] — deferred, pre-existing architectural decision
