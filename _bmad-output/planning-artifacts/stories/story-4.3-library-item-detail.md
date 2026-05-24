# Story 4.3: Library Item Detail View & Copy-to-Clipboard

Status: ready-for-dev

## Story

As an authenticated developer,
I want to open any library item and view its full Markdown content with metadata, copy it to clipboard, and jump to its GitHub source,
so that I can use the skill or prompt immediately in my AI assistant workflow.

## Acceptance Criteria

1. Clicking a library item card from `/library` opens the item detail view (route `/library/{slug}` or inline drawer/modal — see dev notes for approach decision).
2. The detail view renders the full Markdown content with syntax highlighting.
3. The detail view shows metadata: `content_type` badge, title, description, tags, target AI assistants, author (GitHub handle), and last updated date.
4. Clicking "Copy to clipboard" copies the raw Markdown content to the system clipboard and shows a toast notification "Copied to clipboard".
5. Clicking "View on GitHub" opens the source file in a new browser tab pointing to the correct path: `/skills/{slug}/SKILL.md` for skills, `/prompts/{slug}.md` for prompts.
6. `GET /api/v1/library/items/{slug}` with a valid JWT returns all item fields including the full `content` field.
7. `GET /api/v1/library/items/{slug}` for a non-existent slug returns HTTP 404.
8. `GET /api/v1/library/items/{slug}` without a valid JWT returns HTTP 401.
9. Items with `is_public=false` do NOT appear in `GET /api/v1/library/items/public` responses (existing Story 1.2 endpoint — verify not regressed).
10. When the library cache is empty (`library:items` Redis key missing), `GET /api/v1/library/items` and `GET /api/v1/library/items/{slug}` return empty list / 404 without a 500 error.
11. The detail view is keyboard-navigable and meets WCAG 2.1 AA contrast.

## Tasks / Subtasks

- [ ] Backend: Add `GET /api/v1/library/items/{slug}` endpoint to `api/v1/routes/library.py` (AC: 6, 7, 8)
  - [ ] Requires `Annotated[User, Depends(get_current_user)]`
  - [ ] Reads `library:item:{slug}` from Redis (`HGETALL`)
  - [ ] Returns HTTP 404 if slug not found in Redis
  - [ ] Returns `LibraryItemDetail` schema (includes `content` field)
  - [ ] Returns HTTP 401 without valid JWT (via `get_current_user` dependency)
- [ ] Backend: Add `LibraryItemDetail` schema to `schemas/library.py` (AC: 6)
  - [ ] Extends `LibraryItem` by adding `content: str` field
- [ ] Backend: Verify empty cache edge case (AC: 10)
  - [ ] Test that empty Redis returns 404 (not 500) for single item and empty list for collection
- [ ] Backend: Write tests in `tests/test_library.py` (AC: 6–10)
  - [ ] Test detail endpoint with valid slug
  - [ ] Test 404 for non-existent slug
  - [ ] Test 401 without auth
  - [ ] Test `is_public=false` items absent from public endpoint
  - [ ] Test empty cache edge cases
- [ ] Frontend: Add `fetchLibraryItem(slug)` to `api/library.ts` (AC: 6)
- [ ] Frontend: Add `QUERY_KEYS.libraryItem = (slug) => ['library', 'item', slug]` to `queryKeys.ts`
- [ ] Frontend: Create `frontend/src/hooks/useLibraryItem.ts` — TanStack Query hook
- [ ] Frontend: Create `frontend/src/components/LibraryItem/ItemDetail.tsx` (AC: 2, 3, 4, 5, 11)
  - [ ] Render Markdown: use `react-markdown` with `rehype-highlight` (or `react-syntax-highlighter`) for code blocks
  - [ ] Metadata section: `content_type` chip, title, description, tags, target AI chips, author GitHub handle (link to `https://github.com/{author}`), last updated date (formatted)
  - [ ] "Copy to clipboard" button: `navigator.clipboard.writeText(content)` + MUI `Snackbar` toast
  - [ ] "View on GitHub" link: construct URL as `https://github.com/{GITHUB_CONTENT_OWNER}/{GITHUB_CONTENT_REPO}/blob/{GITHUB_CONTENT_BRANCH}/{path}` — path is `skills/{slug}/SKILL.md` or `prompts/{slug}.md`
  - [ ] Write `ItemDetail.test.tsx`
- [ ] Frontend: Decide and implement routing approach for detail view (AC: 1) — see Dev Notes
- [ ] Frontend: Wire navigation from `SkillCard` click to detail view

## Dev Notes

- **Detail view routing approach:** Two options to choose between when implementing:
  - **Option A (recommended):** Dedicated route `/library/{slug}` — `LibraryPage` navigates to it, detail renders as a full page. Simpler, browser history works correctly, deep-linkable.
  - **Option B:** Inline drawer (MUI `<Drawer>`) — opens over the library list. More polished UX but more complex state management. Choose Option A for MVP1 unless there is a strong UX reason to use a drawer.
- **Markdown rendering:** Add `react-markdown` and `rehype-highlight` (or `react-syntax-highlighter`) to frontend dependencies. Render with: `<ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>{content}</ReactMarkdown>`.
- **GitHub source URL construction:** The `GITHUB_CONTENT_OWNER`, `GITHUB_CONTENT_REPO`, and `GITHUB_CONTENT_BRANCH` values are backend config — expose them to the frontend either (a) by including them in the `LibraryItemDetail` response as a `github_url` field (simplest), or (b) via a `/api/v1/config/public` endpoint. Option (a) is recommended for MVP1 — compute the full URL server-side and return it in the schema.
- **Clipboard API:** `navigator.clipboard.writeText()` is modern and supported in all target browsers. No fallback needed per NFR-4.5.1. Wrap in try/catch and show an error toast if it fails (e.g. non-HTTPS context).
- **Toast notifications:** Use MUI `Snackbar` + `Alert` for "Copied to clipboard" feedback. Auto-dismiss after 3 seconds.
- **`LibraryItemDetail` schema:** Add a `github_url: str` field computed server-side as `https://github.com/{owner}/{repo}/blob/{branch}/{path}`. This avoids exposing env var config to the frontend directly.

### Project Structure Notes

- Modify: `backend/src/idp_app/api/v1/routes/library.py` — add detail endpoint
- Modify: `backend/src/idp_app/schemas/library.py` — add `LibraryItemDetail` with `content` + `github_url`
- Modify: `backend/tests/test_library.py`
- Modify: `frontend/src/api/library.ts` — add `fetchLibraryItem`
- Modify: `frontend/src/api/queryKeys.ts`
- Create: `frontend/src/hooks/useLibraryItem.ts`
- Create: `frontend/src/components/LibraryItem/ItemDetail.tsx`
- Create: `frontend/src/components/LibraryItem/ItemDetail.test.tsx`
- Modify: `frontend/src/App.tsx` — add `/library/:slug` route under `<ProtectedRoute>`
- Modify: `frontend/src/components/LibraryItem/SkillCard.tsx` — add click navigation

### References

- Architecture Section 2.3: Redis cache key schema and content structure [Source: _bmad-output/planning-artifacts/architecture.md#23-github-content-service-architecture]
- Architecture Section 2.5: API Surface [Source: _bmad-output/planning-artifacts/architecture.md#25-api-surface]
- PRD FR-5.9, FR-5.10, FR-5.11 [Source: _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md#Feature-5]
- PRD UJ-3: Browsing and Copying a Skill [Source: _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md#uj-3-browsing-and-copying-a-skill]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
