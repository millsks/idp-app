# Story 4.3: Library Item Detail View & Copy-to-Clipboard

Status: done

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

- [x] Backend: Add `GET /api/v1/library/items/{slug}` endpoint to `api/v1/routes/library.py` (AC: 6, 7, 8)
  - [x] Requires `Annotated[User, Depends(get_current_user)]`
  - [x] Reads `library:item:{slug}` from Redis (`HGETALL`)
  - [x] Returns HTTP 404 if slug not found in Redis
  - [x] Returns `LibraryItemDetail` schema (includes `content` field)
  - [x] Returns HTTP 401 without valid JWT (via `get_current_user` dependency)
- [x] Backend: Add `LibraryItemDetail` schema to `schemas/library.py` (AC: 6)
  - [x] Extends `LibraryItem` by adding `content: str` field
- [x] Backend: Verify empty cache edge case (AC: 10)
  - [x] Test that empty Redis returns 404 (not 500) for single item and empty list for collection
- [x] Backend: Write tests in `tests/test_library.py` (AC: 6–10)
  - [x] Test detail endpoint with valid slug
  - [x] Test 404 for non-existent slug
  - [x] Test 401 without auth
  - [x] Test `is_public=false` items absent from public endpoint
  - [x] Test empty cache edge cases
- [x] Frontend: Add `fetchLibraryItem(slug)` to `api/library.ts` (AC: 6)
- [x] Frontend: Add `QUERY_KEYS.libraryItem = (slug) => ['library', 'item', slug]` to `queryKeys.ts`
- [x] Frontend: Create `frontend/src/hooks/useLibraryItem.ts` — TanStack Query hook
- [x] Frontend: Create `frontend/src/components/LibraryItem/ItemDetail.tsx` (AC: 2, 3, 4, 5, 11)
  - [x] Render Markdown: use `react-markdown` with `rehype-highlight` (or `react-syntax-highlighter`) for code blocks
  - [x] Metadata section: `content_type` chip, title, description, tags, target AI chips, author GitHub handle (link to `https://github.com/{author}`), last updated date (formatted)
  - [x] "Copy to clipboard" button: `navigator.clipboard.writeText(content)` + MUI `Snackbar` toast
  - [x] "View on GitHub" link: construct URL as `https://github.com/{GITHUB_CONTENT_OWNER}/{GITHUB_CONTENT_REPO}/blob/{GITHUB_CONTENT_BRANCH}/{path}` — path is `skills/{slug}/SKILL.md` or `prompts/{slug}.md`
  - [x] Write `ItemDetail.test.tsx`
- [x] Frontend: Decide and implement routing approach for detail view (AC: 1) — see Dev Notes
- [x] Frontend: Wire navigation from `SkillCard` click to detail view

### Review Findings

- [x] [Review:Decision] `github_url` type contract — resolved: changed to `str | None` / `string | null`; returns `None` when unconfigured

- [x] [Review:Patch] No slug input validation — path traversal via Redis key construction `backend/src/idp_app/api/v1/routes/library.py:228`
- [x] [Review:Patch] Unknown `content_type` silently maps to `prompts/` path in `_compute_github_url` `backend/src/idp_app/api/v1/routes/library.py:214`
- [x] [Review:Patch] Empty `branch` not guarded in `_compute_github_url` — produces broken `blob//` URL `backend/src/idp_app/api/v1/routes/library.py:210`
- [x] [Review:Patch] Missing 503 test for `get_library_item` Redis error path `backend/tests/test_library.py`
- [x] [Review:Patch] `_DETAIL_STORE` module-level mutable dict — test isolation risk if FakeRedis ever mutates `backend/tests/test_library.py:592`
- [x] [Review:Patch] `_github_settings_dep` uses `types.SimpleNamespace` instead of `Settings.model_construct` — bypasses type checking `backend/tests/test_library.py:107`
- [x] [Review:Patch] `SkillCard` outer `Card` retains `aria-label` after adding `CardActionArea` — conflicting ARIA labels for screen readers `frontend/src/components/LibraryItem/SkillCard.tsx:30`
- [x] [Review:Patch] Invalid `last_updated` date string renders "Invalid Date" — missing `isNaN` guard `frontend/src/components/LibraryItem/ItemDetail.tsx:118`
- [x] [Review:Patch] `item.author` used raw in GitHub profile `href` — must use `encodeURIComponent` `frontend/src/components/LibraryItem/ItemDetail.tsx:216`
- [x] [Review:Patch] `fetchLibraryItem` slug not URL-encoded — malformed URL if slug contains special characters `frontend/src/api/library.ts:58`
- [x] [Review:Patch] `_make_item_hash` omits `content` key when `content=""` — silent test data inconsistency `backend/tests/test_library.py:175`
- [x] [Review:Patch] `beforeAll` and `afterAll` used in `ItemDetail.test.tsx` but not imported from vitest — clipboard tests may not run `frontend/src/components/LibraryItem/ItemDetail.test.tsx:4`
- [x] [Review:Patch] `_DETAIL_FIELDS` omits `target_ai` and `last_updated` — AC 6 under-asserted `backend/tests/test_library.py:91`
- [x] [Review:Patch] `highlight.js` imported directly but not declared as direct dependency in `package.json` — transitive dep fragility
- [x] [Review:Patch] "View on GitHub" `Button` missing `component="a"` — role conflict between `button` and `<a>` semantics (AC 11) `frontend/src/components/LibraryItem/ItemDetail.tsx:172`

- [x] [Review:Defer] `model_dump()` spread into `LibraryItemDetail` constructor — style concern, works correctly today — deferred, pre-existing pattern
- [x] [Review:Defer] `useLibraryItem` missing `staleTime` — causes refetch on every mount — deferred, performance not a bug
- [x] [Review:Defer] `toLocaleDateString` hardcodes `"en-US"` locale — no i18n in project yet — deferred, pre-existing
- [x] [Review:Defer] `handleBack` hardcodes `/library` — breaks browser history for deep-linked users — deferred, UX nice-to-have
- [x] [Review:Defer] Whitespace slug bypasses `enabled: Boolean(slug)` guard — API returns 404 which is handled — deferred, trivial edge case
- [x] [Review:Defer] Redis `hgetall` may return bytes if `decode_responses` not set — pre-existing Redis config concern — deferred, pre-existing
- [x] [Review:Defer] AC 9 regression test uses unusual Redis state (slug in public index with `is_public=false` in hash) — valid but tests failsafe not prevention — deferred, complementary test nice-to-have

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

Claude Sonnet 4.6

### Debug Log References

- Clipboard mock: jsdom 26's `navigator.clipboard` cannot be overridden via `Object.defineProperty` or `vi.spyOn`. Solved using `vi.stubGlobal("navigator", new Proxy(realNavigator, {...}))` which intercepts only the `clipboard` property while preserving all other navigator behaviour.
- Duplicate heading in Markdown test: `mockSkill.content` was initially `"# Python Skill\n\n..."` which clashed with the component's own `<h1>` title. Changed to `"# Skill Overview\n\n..."` so heading queries are unambiguous.
- GitHub link selector clash: test selector `/view.*github/i` matched both the "View source file on GitHub" button AND the author "View alice on GitHub" link. Narrowed selector to `/view source file on github/i` (the `aria-label` on the button).
- `no-floating-promises` on `navigate()`: react-router v7 `navigate()` returns `Promise<void>`; wrapped call sites with `void navigate(...)`.
- `no-misused-promises` on `onClick`: async `handleCopy` passed directly to `onClick` which expects `void` return; fixed to `onClick={() => { void handleCopy(); }}`.
- `no-confusing-void-expression` on Snackbar `onClose`: shorthand arrow returning `setCopySuccess(false)` (void); changed to block body `() => { setCopySuccess(false); }`.
- `prefer-nullish-coalescing`: `||` on nullable `item.target_ai` and `item.author`; changed to `!= null` boolean checks.
- `no-inferrable-types`: explicit `: string` on `slug` param with default; removed annotation (TypeScript infers from default).
- `no-unsafe-return` in Proxy getter: `Reflect.get` returns `any`; suppressed with targeted `eslint-disable-next-line`.
- `LibraryItemDetail` schema added `github_url: str` (computed server-side) so frontend never needs access to `GITHUB_CONTENT_OWNER/REPO/BRANCH` env vars.
- Backend `_CACHE_UNAVAILABLE_MSG` constant: SonarLint S1192 flagged the literal string repeated 3×; extracted to module-level constant.

### Completion Notes List

- Implemented Option A (dedicated route) for detail view routing: `/library/:slug` under `<ProtectedRoute>` in `App.tsx`. Browser history and deep-linking work correctly.
- `LibraryItemDetail` schema extends `LibraryItem` with `content: str` and `github_url: str`. `github_url` is computed server-side in the endpoint using `GITHUB_CONTENT_OWNER/REPO/BRANCH` settings — avoids exposing env vars to frontend.
- `_compute_github_url()` helper in `library.py` returns `""` when owner or repo are not configured, enabling graceful degradation (the "View on GitHub" button is conditionally hidden when `github_url` is empty).
- `SkillCard` wrapped in `MemoryRouter` in tests after adding `useNavigate` — required by react-router.
- All 130 backend tests and 113 frontend tests pass. Coverage: 80.66% backend (threshold: 80%).
- Full quality suite clean: ruff lint + format, mypy, pytest, bandit (backend); ESLint, Prettier, tsc, vitest, audit-ci (frontend).

### File List

- `backend/src/idp_app/schemas/library.py` (modified — added `LibraryItemDetail`)
- `backend/src/idp_app/api/v1/routes/library.py` (modified — added `get_library_item` endpoint, `_compute_github_url` helper, `_CACHE_UNAVAILABLE_MSG` constant)
- `backend/tests/test_library.py` (modified — added `TestLibraryItemDetailEndpoint` class with 10 tests)
- `frontend/src/api/library.ts` (modified — added `LibraryItemDetail` interface and `fetchLibraryItem`)
- `frontend/src/api/queryKeys.ts` (modified — added `libraryItem` query key factory)
- `frontend/src/hooks/useLibraryItem.ts` (created)
- `frontend/src/components/LibraryItem/ItemDetail.tsx` (created)
- `frontend/src/components/LibraryItem/ItemDetail.test.tsx` (created)
- `frontend/src/App.tsx` (modified — added `/library/:slug` route and `ItemDetail` import)
- `frontend/src/components/LibraryItem/SkillCard.tsx` (modified — added `useNavigate` click handler)
- `frontend/src/components/LibraryItem/SkillCard.test.tsx` (modified — wrapped render helper in `MemoryRouter`)
- `frontend/src/api/library.test.ts` (modified — added `fetchLibraryItem` tests)

## Change Log

- **2026-05-25** (Claude Sonnet 4.6): Implemented all ACs — backend `GET /items/{slug}` endpoint,
  `LibraryItemDetail` schema, frontend `ItemDetail` page (Markdown rendering, copy-to-clipboard,
  View on GitHub link), SkillCard navigation wired to detail route. 243 tests passing, full
  quality suite (ruff, mypy, pytest, bandit, ESLint, Prettier, tsc, vitest, audit-ci) clean.
