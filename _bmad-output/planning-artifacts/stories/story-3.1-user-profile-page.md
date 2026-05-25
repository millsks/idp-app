# Story 3.1: User Profile Page & /users/me Endpoints

Status: done

## Story

As an authenticated developer,
I want to see and manage my profile information,
so that I can verify my identity details and personalise my display name on the portal.

## Acceptance Criteria

1. `GET /api/v1/users/me` with a valid JWT Bearer token returns: `id`, `email`, `full_name`, `avatar_url`, `oauth_provider`, `is_active`, `is_superuser`, `created_at`.
2. `GET /api/v1/users/me` without a token or with an expired token returns HTTP 401.
3. `PATCH /api/v1/users/me` with a valid JWT and body `{full_name: "New Name"}` updates the user's display name in the database and returns the updated `UserRead` schema.
4. `PATCH /api/v1/users/me` with an empty or whitespace-only `full_name` returns HTTP 422 with a validation error.
5. `PATCH /api/v1/users/me` without a valid token returns HTTP 401.
6. `PATCH /api/v1/users/me` does NOT affect `is_superuser` status regardless of the request body.
7. The `/profile` page is accessible only to authenticated users — unauthenticated access triggers the `<ProtectedRoute>` redirect to `/login`.
8. The profile page displays: display name, email address (read-only), provider avatar image, account creation date, and OAuth2 provider badge ("GitHub" or "Google").
9. The email field includes a visible read-only label explaining it is sourced from the OAuth provider.
10. Editing the display name and clicking Save calls `PATCH /api/v1/users/me`, updates the displayed name immediately on success.
11. Submitting a blank display name shows an inline validation error — the API is NOT called.
12. The profile page data is loaded via `GET /api/v1/users/me` and managed by TanStack Query (`useQuery`).
13. The display name update uses `useMutation` with optimistic update or immediate cache invalidation on success.

## Tasks / Subtasks

- [x] Backend: Add `get_current_user()` dependency to `core/security.py` (AC: 1, 2)
  - [x] Decode JWT via `decode_access_token`, look up user in DB by username
  - [x] Raise HTTP 401 if token is invalid, expired, or user not found
  - [x] Use `Annotated[User, Depends(get_current_user)]` pattern
- [x] Backend: Add `UserMe` and `UserMeUpdate` schemas to `schemas/user.py` (AC: 1, 3, 4)
  - [x] `UserMe`: `id, email, full_name, avatar_url, oauth_provider, is_active, is_superuser, created_at`
  - [x] `UserMeUpdate`: `full_name: str` with `min_length=1, strip_whitespace=True` validator
- [x] Backend: Add `/users/me` endpoints to `api/v1/routes/users.py` (AC: 1, 2, 3, 4, 5, 6)
  - [x] `GET /users/me` → return `UserMe` for current user
  - [x] `PATCH /users/me` → update `full_name` only, return updated `UserMe`
  - [x] Ensure `is_superuser` is not patchable (only `full_name` field in `UserMeUpdate`)
- [x] Backend: Update tests in `tests/test_users.py` for new endpoints
- [x] Frontend: Add `GET /api/v1/users/me` and `PATCH /api/v1/users/me` to `api/users.ts` (AC: 12, 13)
  - [x] Create `frontend/src/api/users.ts` with typed API functions
- [x] Frontend: Add query keys for users to `api/queryKeys.ts` (or create file) (AC: 12)
  - [x] `QUERY_KEYS.currentUser = () => ['users', 'me']`
- [x] Frontend: Create `ProfilePage.tsx` at `pages/ProfilePage.tsx` (AC: 7–13)
  - [x] `useQuery(QUERY_KEYS.currentUser(), fetchCurrentUser)` to load profile data
  - [x] Display: avatar (`<Avatar>` MUI), display name, email (read-only with label), provider badge chip, account creation date
  - [x] Editable display name field with save button
  - [x] Client-side validation: blank name shows inline error, does not call API (AC: 11)
  - [x] `useMutation` for PATCH — on success invalidate `currentUser` query
  - [x] Loading and error states handled
- [x] Frontend: Register `/profile` route in `App.tsx` wrapped in `<ProtectedRoute>` (AC: 7)
- [x] Frontend: Add profile link to `Layout.tsx` navigation for authenticated users
- [x] Frontend: Write `ProfilePage.test.tsx`

## Dev Notes

- `get_current_user()` in `core/security.py` uses the existing `decode_access_token()` function (python-jose, HS256). Extract the username/subject from the token payload, query the DB for the user. This dependency is used by ALL future authenticated endpoints.
- `UserMe` schema is separate from any existing `UserRead` schemas — check `schemas/user.py` for what already exists and extend thoughtfully rather than replacing.
- The `UserMeUpdate` schema should use Pydantic v2's `model_validator` or `field_validator` to strip whitespace and enforce `min_length=1`. Do NOT allow a user to set their name to spaces.
- For the frontend, `useAuth().user` (populated during login) can be used as the initial data hint for TanStack Query — set `initialData` from AuthContext if available to avoid a loading flash on first render.
- Avatar rendering: use MUI `<Avatar src={user.avatar_url}>` with a fallback to the user's initials if `avatar_url` is null.
- Account creation date: format as "Member since May 2026" using `date-fns` or `Intl.DateTimeFormat`.
- The `oauth_provider` field drives the provider badge: map `"github"` → GitHub icon/chip, `"google"` → Google icon/chip.

### Project Structure Notes

- Modify: `backend/src/idp_app/core/security.py` — add `get_current_user()` dependency
- Modify: `backend/src/idp_app/schemas/user.py` — add `UserMe`, `UserMeUpdate`
- Modify: `backend/src/idp_app/api/v1/routes/users.py` — add `/me` GET and PATCH
- Modify: `backend/tests/test_users.py`
- Create: `frontend/src/api/users.ts`
- Create: `frontend/src/api/queryKeys.ts` (if not already created in Story 1.2)
- Create: `frontend/src/pages/ProfilePage.tsx`
- Create: `frontend/src/pages/ProfilePage.test.tsx`
- Modify: `frontend/src/App.tsx` — add `/profile` route under `<ProtectedRoute>`
- Modify: `frontend/src/components/Layout/Layout.tsx` — add profile navigation link

### References

- Architecture Section 3.2: Backend Patterns — `get_current_user` dependency [Source: _bmad-output/planning-artifacts/architecture.md#32-backend-patterns]
- Architecture Section 2.5: API Surface [Source: _bmad-output/planning-artifacts/architecture.md#25-api-surface]
- PRD FR-3.1 – FR-3.6 [Source: _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md#Feature-3]
- Copilot Instructions — Backend patterns: Annotated Depends, response_model, status codes [Source: .github/copilot-instructions.md]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

- Fixed `vi.fn` mock spreading extra TanStack Query v5 context argument to `mockPatchMe` — scoped mock to forward only first argument.
- Fixed disabled Save button blocking AC-11 test — removed `editedName.trim() === ""` from disabled condition, deferred blank-name guard to `handleSave()` so the inline error renders.

### Completion Notes List

- Added `get_current_user()` FastAPI dependency to `core/security.py` using `OAuth2PasswordBearer`, `decode_access_token`, and DB lookup by `username` claim. No circular imports — `models.user` → `core.database` is one-way.
- Added `UserMe` (read schema) and `UserMeUpdate` (write schema with `@field_validator` for whitespace stripping) to `schemas/user.py`.
- Added `GET /users/me` and `PATCH /users/me` endpoints to `api/v1/routes/users.py`, placed BEFORE `/{user_id}` to avoid path capture. Only `full_name` is patchable via `UserMeUpdate`; `is_superuser` is protected by schema design.
- Backend test suite: all pre-existing `TestCurrentUserEndpoints` tests (written in a prior session) now pass — 82/82. Coverage 82%.
- Created `frontend/src/api/users.ts` with `fetchMe()` and `patchMe()` typed against `UserMe` / `UserMeUpdate` interfaces.
- Created `frontend/src/api/queryKeys.ts` with `QUERY_KEYS.currentUser` factory.
- Created `ProfilePage.tsx` with: `useQuery` for load, `useMutation` + `invalidateQueries` on save, MUI `Avatar` with initials fallback, read-only email field with helper text, editable display name with `handleSave` validation, `ProviderBadge` chip (GitHub/Google), `Intl.DateTimeFormat` for member-since date, loading spinner, error alert.
- Replaced `/profile` route placeholder in `App.tsx` with `<ProfilePage />`.
- Added `AUTHED_NAV_ITEMS` with Profile link (AccountCircleIcon) to `Layout.tsx`, merged conditionally when `isAuthenticated`.
- Created `ProfilePage.test.tsx` with 9 tests covering ACs 8–13. All 54 frontend tests pass.

### File List

- `backend/src/idp_app/core/security.py` — modified (added `oauth2_scheme`, `get_current_user`)
- `backend/src/idp_app/schemas/user.py` — modified (added `UserMe`, `UserMeUpdate`)
- `backend/src/idp_app/api/v1/routes/users.py` — modified (added GET/PATCH `/me` endpoints)
- `frontend/src/api/users.ts` — created
- `frontend/src/api/queryKeys.ts` — created
- `frontend/src/pages/ProfilePage.tsx` — created
- `frontend/src/pages/ProfilePage.test.tsx` — created
- `frontend/src/App.tsx` — modified (import + replace profile route placeholder)
- `frontend/src/components/Layout/Layout.tsx` — modified (added Profile nav link for authenticated users)

### Review Findings

- [x] [Review][Decision] Loading spinner is dead code in production — `placeholderData` is always populated on `/profile` (protected route, `authUser` is always present), so `isLoading` is always `false` and the spinner block is never reached in production. The spinner test passes only because the `useAuth` mock returns `user: null`, making `placeholderData` absent in the test harness. Options: (A) Keep `placeholderData`, remove the spinner guard entirely since it serves no purpose. (B) Replace `placeholderData` with `initialData` so TanStack Query treats it as real data and `isLoading` behaves correctly. (C) Change spinner guard to `isFetching && !profile` to show a background-refetch indicator instead. [frontend/src/pages/ProfilePage.tsx:145]
- [x] [Review][Patch] `if (profile && !initialized)` setState call in render body — calling `setEditedName` / `setInitialized` directly in the render function body causes an extra render on every initial mount and is a React anti-pattern. Replace with `useEffect(() => { if (profile) { setEditedName(profile.full_name ?? ""); setInitialized(true); } }, [profile])`. [frontend/src/pages/ProfilePage.tsx:116]
- [x] [Review][Defer→Fixed] `oauth2_scheme` hardcodes token URL string `/api/v1/auth/token` — fixed: now derived from `settings.API_V1_PREFIX`. [backend/src/idp_app/core/security.py]

### Change Log

- feat(backend): add get_current_user FastAPI dependency (AC: 1, 2, 5) — 2026-05-24
- feat(backend): add UserMe and UserMeUpdate Pydantic schemas (AC: 1, 3, 4) — 2026-05-24
- feat(backend): add GET /users/me and PATCH /users/me endpoints (AC: 1–6) — 2026-05-24
- feat(frontend): create api/users.ts and api/queryKeys.ts (AC: 12, 13) — 2026-05-24
- feat(frontend): create ProfilePage with full AC 7–13 coverage — 2026-05-24
- feat(frontend): wire /profile route and Profile nav link (AC: 7) — 2026-05-24
