# Story 4.4: Library Write — Create, Edit & Delete Skills/Prompts

Status: ready-for-dev

## Story

As an admin/maintainer user,
I want to create, edit, and delete skills and prompts directly from the app,
so that I can manage the content in `millsks/idp-reusable-skills-prompts` without leaving the portal.

## Background

Content is stored in the GitHub repo `millsks/idp-reusable-skills-prompts` as Markdown files with YAML frontmatter:

- Skills: `skills/{slug}/SKILL.md`
- Prompts: `prompts/{slug}.md`

Frontmatter schema:

```yaml
---
title: Human-readable title
description: Short description (1–2 sentences)
tags:
  - tag-one
  - tag-two
is_public: true
target_ai:
  - ChatGPT
  - Claude
---

# Title

Full Markdown content here.
```

Write operations commit files directly to the `GITHUB_CONTENT_BRANCH` branch via the GitHub Contents API (PUT for create/update, DELETE for delete), then immediately trigger a `library.sync_content` resync task so the Redis cache reflects the change.

## Acceptance Criteria

### Admin access
1. Only users with `User.is_admin = true` may call the write endpoints. All write endpoints return HTTP 403 for non-admin authenticated users and HTTP 401 for unauthenticated requests.
2. The `is_admin` field is added to the `users` table via an Alembic migration. Default value is `false`.

### Create
3. `POST /api/v1/library/items` accepts a JSON body with: `slug`, `title`, `description`, `content_type` (`Skill` or `Prompt`), `content` (Markdown body, no frontmatter), `tags` (list), `target_ai` (list, optional), `is_public` (bool).
4. The endpoint constructs the correct file path (`skills/{slug}/SKILL.md` or `prompts/{slug}.md`), builds the YAML frontmatter, and commits the file to GitHub via the Contents API.
5. If a file at the derived path already exists on GitHub, the endpoint returns HTTP 409 Conflict.
6. After a successful commit, the endpoint enqueues a `library.sync_content` Celery task and returns HTTP 201 with the created item's slug and GitHub commit SHA.

### Update
7. `PUT /api/v1/library/items/{slug}` accepts the same body as POST (all fields optional except `content`). The endpoint fetches the current file SHA from GitHub, builds a new file with updated frontmatter + content, and commits the update.
8. If the slug does not exist in Redis or on GitHub, the endpoint returns HTTP 404.
9. After a successful update, the endpoint enqueues a resync and returns HTTP 200 with the updated slug and commit SHA.

### Delete
10. `DELETE /api/v1/library/items/{slug}` fetches the current file SHA and deletes the file from GitHub via the Contents API.
11. After deletion the endpoint removes the item from Redis (`library:item:{slug}` hash, `library:items` set, `library:items:public` set) immediately (optimistic cache invalidation), then enqueues a full resync.
12. Returns HTTP 204 No Content on success. Returns HTTP 404 if the slug does not exist.

### Frontend
13. An "Add Entry" button (admin users only) appears on `LibraryPage`. Clicking it opens a full-page form at `/library/new`.
14. The create/edit form fields: Title (text), Slug (text, auto-generated from title, editable), Description (text), Content Type toggle (Skill / Prompt), Tags (chip input), Target AI (multi-select chips: ChatGPT, Claude, Gemini, Other), Is Public (toggle), Content (split-pane Markdown editor — textarea left, live `react-markdown` preview right).
15. Form validation: Title and Content are required. Slug must match `^[a-z0-9-]+$`. Duplicate slug shows an inline error on submit.
16. On successful create, the user is redirected to `/library/{slug}` (the new item's detail page).
17. An "Edit" button (admin only) appears on the item detail page (`/library/{slug}`). Clicking it opens `/library/{slug}/edit` pre-populated with current item data.
18. On successful update, the user is redirected back to `/library/{slug}`.
19. A "Delete" button with a confirmation dialog (admin only) appears on the item detail page. Confirming deletes the item and redirects to `/library`.
20. All write actions show a loading state on the submit/confirm button while the request is in flight.
21. API errors (409 conflict, 404, 503 broker unavailable) are shown as inline form errors or toast notifications.

## Tasks / Subtasks

### Backend

- [ ] Add `is_admin: Mapped[bool]` field to `User` model in `models/user.py` (AC: 2)
  - [ ] Default: `False`
  - [ ] Add to `__repr__`
- [ ] Generate Alembic migration: `pixi run backend-migration -m "add_is_admin_to_users"` (AC: 2)
- [ ] Add `require_admin` dependency to `core/security.py` (AC: 1)
  - [ ] Calls `get_current_user`, raises `HTTP 403` if `user.is_admin` is `False`
- [ ] Add `LibraryItemCreate`, `LibraryItemUpdate`, `LibraryItemWriteResponse` schemas to `schemas/library.py` (AC: 3, 7)
- [ ] Add `build_frontmatter_content(item: LibraryItemCreate) -> str` helper to `services/github_content.py` (AC: 4)
  - [ ] Outputs well-formed YAML frontmatter block + `\n\n` + content body
- [ ] Add `get_file_sha(client, owner, repo, path, *, token, ref) -> str` helper to `services/github_content.py` (AC: 7, 10)
  - [ ] Uses Contents API to fetch the blob SHA of an existing file; raises `HTTPStatusError` on 404
- [ ] Add `create_or_update_file(client, owner, repo, path, content_b64, message, *, token, sha=None) -> str` helper to `services/github_content.py` (AC: 4, 7)
  - [ ] Returns the commit SHA from the response
- [ ] Add `delete_file(client, owner, repo, path, sha, message, *, token) -> str` helper to `services/github_content.py` (AC: 10)
  - [ ] Returns the commit SHA
- [ ] Add `POST /api/v1/library/items` endpoint to `routes/library.py` (AC: 3–6)
  - [ ] `Depends(require_admin)`
  - [ ] Check slug does not already exist in Redis; if it does return 409 (fast path before hitting GitHub)
  - [ ] Build path, frontmatter, commit to GitHub
  - [ ] Enqueue `sync_library_content.delay()`
  - [ ] Return 201 `LibraryItemWriteResponse`
- [ ] Add `PUT /api/v1/library/items/{slug}` endpoint (AC: 7–9)
  - [ ] `Depends(require_admin)`
  - [ ] Fetch current item from Redis; 404 if not found
  - [ ] Fetch file SHA from GitHub
  - [ ] Rebuild frontmatter + content, commit update
  - [ ] Enqueue resync
  - [ ] Return 200 `LibraryItemWriteResponse`
- [ ] Add `DELETE /api/v1/library/items/{slug}` endpoint (AC: 10–12)
  - [ ] `Depends(require_admin)`
  - [ ] Fetch file SHA from GitHub; 404 if not found
  - [ ] Delete file on GitHub
  - [ ] Optimistic cache invalidation (remove from Redis immediately)
  - [ ] Enqueue resync
  - [ ] Return 204
- [ ] Write tests in `tests/test_library_write.py` (AC: 1–12)
  - [ ] Test 401 / 403 access control for all three endpoints
  - [ ] Test create: success (201 + correct file path + resync enqueued)
  - [ ] Test create: 409 when slug already in Redis
  - [ ] Test update: success (200 + commit SHA returned)
  - [ ] Test update: 404 when slug not in Redis
  - [ ] Test delete: success (204 + item removed from Redis)
  - [ ] Test delete: 404 when slug not found on GitHub
  - [ ] Mock `httpx.AsyncClient` and Celery `.delay()` in all tests

### Frontend

- [ ] Install `@uiw/react-md-editor` (or equivalent lightweight split-pane MD editor) — or implement manually with a textarea + `<ReactMarkdown>` preview pane (no extra dep)
- [ ] Create `frontend/src/api/libraryWrite.ts` — typed API functions
  - [ ] `createLibraryItem(data: LibraryItemCreate): Promise<LibraryItemWriteResponse>`
  - [ ] `updateLibraryItem(slug: string, data: LibraryItemUpdate): Promise<LibraryItemWriteResponse>`
  - [ ] `deleteLibraryItem(slug: string): Promise<void>`
- [ ] Add mutation query keys / hooks
  - [ ] `useCreateLibraryItem` (TanStack `useMutation`, invalidates `QUERY_KEYS.libraryItems`)
  - [ ] `useUpdateLibraryItem` (TanStack `useMutation`, invalidates `QUERY_KEYS.libraryItem(slug)` + items list)
  - [ ] `useDeleteLibraryItem` (TanStack `useMutation`, invalidates items list)
- [ ] Create `frontend/src/pages/LibraryNewPage.tsx` (AC: 13–16, 20, 21)
  - [ ] Route: `/library/new` (admin-only, wrap in `AdminRoute` or check `user.is_admin`)
  - [ ] Split-pane Markdown editor component (textarea + live `<ReactMarkdown>` preview, side-by-side on md+, stacked on mobile)
  - [ ] Auto-generates slug from title (`title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')`)
  - [ ] Form validation via React controlled inputs (no form library needed for MVP1)
  - [ ] On success: navigate to `/library/{slug}`
- [ ] Create `frontend/src/pages/LibraryEditPage.tsx` (AC: 17–18, 20, 21)
  - [ ] Route: `/library/:slug/edit`
  - [ ] Pre-populates form from `useLibraryItem(slug)` query
  - [ ] Reuses the same form layout/components as `LibraryNewPage`
  - [ ] On success: navigate to `/library/{slug}`
- [ ] Add "Add Entry" button to `LibraryPage` (admin only) linking to `/library/new` (AC: 13)
- [ ] Add "Edit" and "Delete" buttons to `ItemDetail` component (admin only) (AC: 17, 19)
  - [ ] Delete: MUI `Dialog` confirmation before calling `deleteLibraryItem`
  - [ ] On delete success: navigate to `/library`
- [ ] Wire new routes in `App.tsx` under admin-protected route (AC: 13, 17)
- [ ] Write `LibraryNewPage.test.tsx` and `LibraryEditPage.test.tsx`

## Dev Notes

- **GitHub PAT scope:** The `GITHUB_CONTENT_TOKEN` used in Story 4.1 must have `contents:write` permission (not just read) for this story. Update `.env.example` and deployment docs.
- **Split-pane editor without extra dependencies:** A simple two-column `<Grid2>` — left: `<TextField multiline>` for the content body, right: `<Box>` with `<ReactMarkdown>` rendering the current value — avoids adding a new package. `react-markdown` is already used in Story 4.3.
- **Slug uniqueness:** The Redis `library:items` set is the authoritative fast-path check for slug conflicts. The GitHub API is the authoritative source but adds latency — check Redis first.
- **File path derivation:** Same logic as `derive_slug` / `derive_content_type` in `services/github_content.py`. Expose a `derive_path(slug, content_type) -> str` helper: `skills/{slug}/SKILL.md` or `prompts/{slug}.md`.
- **Commit messages:** Standard format: `feat(library): add skill {slug}` / `fix(library): update prompt {slug}` / `chore(library): delete skill {slug}`.
- **`AdminRoute` component:** Create `frontend/src/components/AdminRoute/AdminRoute.tsx` — wraps `<ProtectedRoute>` and additionally checks `user.is_admin`; redirects to `/library` with a "Not authorised" toast if `is_admin` is false.
- **`user.is_admin` in frontend:** The `/api/v1/users/me` response (`UserRead` schema) must include `is_admin`. Add it to the `UserRead` schema if not already present.

### Project Structure Notes

- Modify: `backend/src/idp_app/models/user.py` — add `is_admin`
- Create: `backend/alembic/versions/YYYYMMDD_HHMM_*_add_is_admin_to_users.py`
- Modify: `backend/src/idp_app/core/security.py` — add `require_admin`
- Modify: `backend/src/idp_app/schemas/library.py` — add write schemas
- Modify: `backend/src/idp_app/schemas/users.py` — add `is_admin` to `UserRead`
- Modify: `backend/src/idp_app/services/github_content.py` — add write helpers
- Modify: `backend/src/idp_app/api/v1/routes/library.py` — add write endpoints
- Create: `backend/tests/test_library_write.py`
- Create: `frontend/src/api/libraryWrite.ts`
- Create: `frontend/src/hooks/useLibraryWrite.ts`
- Create: `frontend/src/components/AdminRoute/AdminRoute.tsx`
- Create: `frontend/src/components/AdminRoute/AdminRoute.test.tsx`
- Create: `frontend/src/pages/LibraryNewPage.tsx`
- Create: `frontend/src/pages/LibraryNewPage.test.tsx`
- Create: `frontend/src/pages/LibraryEditPage.tsx`
- Create: `frontend/src/pages/LibraryEditPage.test.tsx`
- Modify: `frontend/src/pages/LibraryPage.tsx` — "Add Entry" button (admin only)
- Modify: `frontend/src/components/LibraryItem/ItemDetail.tsx` — Edit/Delete buttons (admin only)
- Modify: `frontend/src/App.tsx` — new routes

### References

- Architecture Section 2.3: GitHub Content Service [Source: _bmad-output/planning-artifacts/architecture.md]
- Architecture Section 2.5: API Surface [Source: _bmad-output/planning-artifacts/architecture.md]
- Story 4.1: GitHub Content Sync (Redis cache schema) [Source: _bmad-output/planning-artifacts/stories/story-4.1-github-content-sync.md]
- Story 4.2: Library Browse (list endpoint) [Source: _bmad-output/planning-artifacts/stories/story-4.2-library-browse-search-filter.md]
- Story 4.3: Item Detail (detail endpoint + `ItemDetail` component) [Source: _bmad-output/planning-artifacts/stories/story-4.3-library-item-detail.md]

## Dev Agent Record

### Agent Model Used

### Debug Log References
