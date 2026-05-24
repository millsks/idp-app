# Story 3.1: User Profile Page & /users/me Endpoints

Status: ready-for-dev

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

- [ ] Backend: Add `get_current_user()` dependency to `core/security.py` (AC: 1, 2)
  - [ ] Decode JWT via `decode_access_token`, look up user in DB by username
  - [ ] Raise HTTP 401 if token is invalid, expired, or user not found
  - [ ] Use `Annotated[User, Depends(get_current_user)]` pattern
- [ ] Backend: Add `UserMe` and `UserMeUpdate` schemas to `schemas/user.py` (AC: 1, 3, 4)
  - [ ] `UserMe`: `id, email, full_name, avatar_url, oauth_provider, is_active, is_superuser, created_at`
  - [ ] `UserMeUpdate`: `full_name: str` with `min_length=1, strip_whitespace=True` validator
- [ ] Backend: Add `/users/me` endpoints to `api/v1/routes/users.py` (AC: 1, 2, 3, 4, 5, 6)
  - [ ] `GET /users/me` → return `UserMe` for current user
  - [ ] `PATCH /users/me` → update `full_name` only, return updated `UserMe`
  - [ ] Ensure `is_superuser` is not patchable (only `full_name` field in `UserMeUpdate`)
- [ ] Backend: Update tests in `tests/test_users.py` for new endpoints
- [ ] Frontend: Add `GET /api/v1/users/me` and `PATCH /api/v1/users/me` to `api/users.ts` (AC: 12, 13)
  - [ ] Create `frontend/src/api/users.ts` with typed API functions
- [ ] Frontend: Add query keys for users to `api/queryKeys.ts` (or create file) (AC: 12)
  - [ ] `QUERY_KEYS.currentUser = () => ['users', 'me']`
- [ ] Frontend: Create `ProfilePage.tsx` at `pages/ProfilePage.tsx` (AC: 7–13)
  - [ ] `useQuery(QUERY_KEYS.currentUser(), fetchCurrentUser)` to load profile data
  - [ ] Display: avatar (`<Avatar>` MUI), display name, email (read-only with label), provider badge chip, account creation date
  - [ ] Editable display name field with save button
  - [ ] Client-side validation: blank name shows inline error, does not call API (AC: 11)
  - [ ] `useMutation` for PATCH — on success invalidate `currentUser` query
  - [ ] Loading and error states handled
- [ ] Frontend: Register `/profile` route in `App.tsx` wrapped in `<ProtectedRoute>` (AC: 7)
- [ ] Frontend: Add profile link to `Layout.tsx` navigation for authenticated users
- [ ] Frontend: Write `ProfilePage.test.tsx`

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

### Debug Log References

### Completion Notes List

### File List
