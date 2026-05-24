# Story 1.2: Public Preview Strip

Status: ready-for-dev

## Story

As a public visitor,
I want to see a preview of real skills and prompts on the landing page,
so that I can evaluate the library's content quality before committing to sign up.

## Acceptance Criteria

1. The landing page displays a preview strip of up to 6 public library items when the cache is populated.
2. Each preview card shows: title, description, `content_type` badge (Skill / Prompt), and tags.
3. Full Markdown content is NOT displayed in the preview strip cards.
4. Clicking a preview card when unauthenticated shows title and description only, plus a "Sign in to view full content" CTA — full content is NOT shown.
5. When the library cache is empty or the API returns an error, the preview strip is hidden or shows a graceful placeholder; the rest of the landing page renders correctly.
6. `GET /api/v1/library/items/public` returns HTTP 200 with public items when called without an auth token.
7. The endpoint returns only items where `is_public=true`.
8. The preview strip is keyboard-navigable and meets WCAG 2.1 AA contrast.

## Tasks / Subtasks

- [ ] Backend: Add `GET /api/v1/library/items/public` endpoint (AC: 6, 7)
  - [ ] Create `backend/src/idp_app/api/v1/routes/library.py` with the public endpoint
  - [ ] Endpoint reads from Redis key `library:items:public` (Set of slugs) then fetches each `library:item:{slug}` Hash
  - [ ] Returns `LibraryItemList` schema (standard envelope: `{items, total, page, size, pages}`)
  - [ ] No auth dependency — endpoint is fully public
  - [ ] Returns empty list (not 500) when Redis has no `library:items:public` key
  - [ ] Register router in `backend/src/idp_app/api/v1/router.py`
- [ ] Backend: Add `LibraryItem` and `LibraryItemList` Pydantic schemas (AC: 6)
  - [ ] Create `backend/src/idp_app/schemas/library.py`
  - [ ] `LibraryItem`: `slug`, `title`, `description`, `content_type`, `tags`, `is_public`, `target_ai`, `author`, `last_updated` (no `content` field in list schema)
  - [ ] `LibraryItemList`: standard envelope `{items: list[LibraryItem], total, page, size, pages}`
- [ ] Frontend: Create `PublicPreviewStrip` component (AC: 1, 2, 3, 5, 8)
  - [ ] Create `frontend/src/components/LandingPreview/PublicPreviewStrip.tsx`
  - [ ] Call `GET /api/v1/library/items/public` via `apiClient` (no auth header needed)
  - [ ] Render up to 6 item cards using MUI `Card` components
  - [ ] Each card: title, description, `content_type` chip, tags chips
  - [ ] Handle empty/error state gracefully (hidden/placeholder)
- [ ] Frontend: Wire preview item click behaviour (AC: 4)
  - [ ] Clicking a card opens a modal or inline teaser showing title + description only
  - [ ] "Sign in to view full content" CTA button links to `/login`
  - [ ] Full Markdown content is never fetched or rendered for unauthenticated users
- [ ] Frontend: Add `PublicPreviewStrip` to `HomePage.tsx` (AC: 1)
- [ ] Backend: Write tests for public library endpoint in `tests/test_library.py`
- [ ] Frontend: Write tests for `PublicPreviewStrip.test.tsx`

## Dev Notes

- The library cache (Redis) may be empty at the time this story is first tested — that is expected. Seed the content repo first, or mock Redis in tests.
- The `library.py` routes file is brand new. Follow the pattern of existing route files (`health.py`, `users.py`): export a `router = APIRouter()`, use `Annotated[T, Depends(f)]` for all dependencies.
- `get_redis()` dependency must exist in `core/database.py` before this story. If it does not, add it as part of this story's tasks.
- The public endpoint does NOT need `get_current_user` — do not add an auth dependency to it.
- Standard response envelope: all list endpoints return `{items, total, page, size, pages}` — see Architecture Section 3.2.
- `content` (full Markdown) is intentionally absent from the `LibraryItem` schema used by list/public endpoints. Full content is only returned by the single-item detail endpoint (Story 4.3).

### Project Structure Notes

- Create: `backend/src/idp_app/api/v1/routes/library.py`
- Create: `backend/src/idp_app/schemas/library.py`
- Modify: `backend/src/idp_app/api/v1/router.py` — register library router
- Modify: `backend/src/idp_app/core/database.py` — add `get_redis()` if not present
- Create: `frontend/src/components/LandingPreview/PublicPreviewStrip.tsx`
- Create: `frontend/src/components/LandingPreview/PublicPreviewStrip.test.tsx`
- Modify: `frontend/src/pages/HomePage.tsx` — add `<PublicPreviewStrip />`
- Create: `backend/tests/test_library.py`

### References

- PRD FR-1.6 [Source: _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md#Feature-1]
- PRD FR-5.2, FR-5.5 [Source: _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md#Feature-5]
- Architecture ARCH-12 (standard envelope), ARCH-14 (public endpoint) [Source: _bmad-output/planning-artifacts/architecture.md#25-api-surface]
- Architecture Section 4: Redis cache key schema [Source: _bmad-output/planning-artifacts/architecture.md#23-github-content-service-architecture]
- Architecture Section 3.2: Backend Patterns [Source: _bmad-output/planning-artifacts/architecture.md#32-backend-patterns]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
