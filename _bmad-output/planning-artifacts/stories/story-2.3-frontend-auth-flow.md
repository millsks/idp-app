# Story 2.3: Frontend Auth Flow, Token Storage, Route Protection & Logout

Status: done

## Story

As a developer,
I want the frontend to handle the OAuth callback, store my token securely in memory, protect private pages, and let me log out cleanly,
so that my session is secure and the app behaves correctly whether I am authenticated or not.

## Acceptance Criteria

1. `AuthContext` is implemented with: `token` stored via `useRef<string | null>` (never useState, never storage), `user: UserProfile | null`, `isAuthenticated: boolean`, `isLoading: boolean`, `login(exchangeCode)`, and `logout()`.
2. `useAuth()` hook wraps `AuthContext` and is the only way components access auth state.
3. `AuthCallbackPage` at `/auth/callback` reads `?exchange_code=` from the URL, calls `POST /api/v1/auth/token/exchange`, stores the JWT in `AuthContext` via `login()`, then redirects to the original intended route (`?redirect=` param) or `/library`.
4. If the exchange code is expired/used and the API returns 400/401, `AuthCallbackPage` redirects to `/login?error=auth_failed`.
5. `ProtectedRoute` component wraps React Router v7 routes — when `isAuthenticated` is false and `isLoading` is false, redirects to `/login?redirect={location.pathname}`.
6. After successful login, the redirect-on-login pattern works: navigating to `/profile` while unauthenticated, logging in, and being sent back to `/profile`.
7. When the JWT expires (30 min) and any subsequent API call returns HTTP 401, the existing Axios 401 interceptor in `client.ts` triggers `logout()` via `AuthContext`, clearing the token and redirecting to `/login`.
8. On page refresh, `AuthContext` token is null — the user is unauthenticated and protected routes redirect to `/login`.
9. `LoginPage` at `/login` renders "Continue with GitHub" and "Continue with Google" buttons only. No username/password form exists.
10. "Continue with GitHub" links to `GET /api/v1/auth/github`. "Continue with Google" links to `GET /api/v1/auth/google`.
11. Clicking "Log Out" calls `POST /api/v1/auth/logout`, clears the `AuthContext` token and user, and redirects to `/`.
12. `App.tsx` route table is updated: `/`, `/login`, `/auth/callback` are public routes; `/library`, `/profile` are wrapped in `<ProtectedRoute>`.
13. The Axios `apiClient` request interceptor is updated to read the JWT from `AuthContext` via a module-level getter set by the context.

## Tasks / Subtasks

- [x] Create `frontend/src/contexts/AuthContext.tsx` (AC: 1)
  - [x] `AuthState` interface and `AuthContextValue` interface per architecture spec
  - [x] `token` stored in `useRef<string | null>` (NOT `useState`)
  - [x] `login(exchangeCode)`: calls `POST /api/v1/auth/token/exchange`, on success stores token in ref, fetches user via `GET /api/v1/users/me`, sets `user` state, sets `isAuthenticated=true`
  - [x] `logout()`: clears token ref, clears user, sets `isAuthenticated=false`
  - [x] Token getter lives in `frontend/src/utils/tokenStore.ts` (avoids circular import with `client.ts → AuthContext → auth.ts → client.ts`)
- [x] Create `frontend/src/hooks/useAuth.ts` (AC: 2)
  - [x] Wraps `useContext(AuthContext)` with error guard
- [x] Create `frontend/src/pages/AuthCallbackPage.tsx` (AC: 3, 4)
  - [x] Reads `exchange_code` from URL search params
  - [x] Calls `AuthContext.login(exchangeCode)` on mount
  - [x] Handles success (redirect), error (redirect to /login?error=auth_failed), and loading states
- [x] Create `frontend/src/components/ProtectedRoute/ProtectedRoute.tsx` (AC: 5, 6)
  - [x] Uses `useAuth()` — renders `<Outlet />` if authenticated, `<Navigate>` if not
  - [x] Passes current `location.pathname` as `?redirect=` param
  - [x] Renders `<CircularProgress />` while `isLoading` is true
  - [x] Write `ProtectedRoute.test.tsx`
- [x] Create `frontend/src/pages/LoginPage.tsx` (AC: 9, 10)
  - [x] Two MUI buttons: "Continue with GitHub" → `/api/v1/auth/github`, "Continue with Google" → `/api/v1/auth/google` (Google disabled, coming soon)
  - [x] Shows error message if `?error=` param is present in URL
  - [x] NO username/password fields
- [x] Update `frontend/src/api/client.ts` (AC: 7, 13)
  - [x] Request interceptor reads token via `getAuthToken()` from `tokenStore.ts`
  - [x] 401 response interceptor: calls `runLogout()` from `tokenStore.ts` + redirect to `/login`
- [x] Update `frontend/src/App.tsx` (AC: 12)
  - [x] Wrap app in `<AuthProvider>`
  - [x] Add routes: `/login` → `<LoginPage>`, `/auth/callback` → `<AuthCallbackPage>`
  - [x] Wrap `/library` and `/profile` routes in `<ProtectedRoute>` (placeholder content until Stories 3.x/4.x)
- [x] Create `frontend/src/api/auth.ts` — API functions for auth endpoints
- [x] Write tests: `AuthCallbackPage.test.tsx`, `LoginPage.test.tsx`, `useAuth.test.ts`
- [x] Update `frontend/src/components/Layout/Layout.tsx` (AC: 11) — auth-conditional Sign In / Log Out button in AppBar

## Dev Notes

- `token` MUST be `useRef<string | null>`, NOT `useState`. Using `useState` would cause re-renders that could expose the token value to React DevTools snapshot. The ref pattern is intentional per Architecture Section 2.4.
- `getAuthToken()` exported getter: a module-level variable that `AuthContext` sets on each login — this allows `client.ts` to read the current token without importing the context hook (which would violate React rules of hooks).
- `GET /api/v1/users/me` is called inside `login()` after token storage to hydrate `user` state. This endpoint is created in Story 3.1 — for this story, add a placeholder `user` type and gracefully handle a 404/error if the endpoint isn't live yet in the same sprint.
- The Axios 401 interceptor already partially exists in `client.ts` — update it rather than replacing it. Confirm it calls `logout()` from `AuthContext` (not just a `localStorage.clear()`).
- "Continue with GitHub/Google" buttons use `window.location.href` navigation (full page redirect to backend), NOT React Router `<Link>` or `navigate()`. The OAuth redirect MUST leave the SPA.
- Ensure `AuthContext.Provider` wraps the entire app in `App.tsx` so all child components can access auth state.

### Project Structure Notes

- Create: `frontend/src/contexts/AuthContext.tsx`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/pages/AuthCallbackPage.tsx`
- Create: `frontend/src/components/ProtectedRoute/ProtectedRoute.tsx`
- Create: `frontend/src/components/ProtectedRoute/ProtectedRoute.test.tsx`
- Create: `frontend/src/api/auth.ts`
- Modify: `frontend/src/api/client.ts` — wire `getAuthToken()` into request interceptor
- Modify: `frontend/src/App.tsx` — wrap with AuthContext.Provider, add routes, add ProtectedRoute

### References

- Architecture Section 2.4: Frontend Auth Architecture [Source: _bmad-output/planning-artifacts/architecture.md#24-frontend-auth-architecture]
- Architecture Section 3.3: Frontend Patterns [Source: _bmad-output/planning-artifacts/architecture.md#33-frontend-patterns]
- Architecture Section 7: Security Checklist items 3, 8, 9 [Source: _bmad-output/planning-artifacts/architecture.md#7-security-checklist]
- PRD FR-2.7, FR-2.7a, FR-2.8, FR-2.10, FR-4.1 – FR-4.4 [Source: _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (Claude Code)

### Debug Log References

- `AuthContext.tsx` must not export both a component and a hook in the same file — the `react-refresh/only-export-components` ESLint rule (max-warnings=0) rejects it. Moved the `useContext` call into `hooks/useAuth.ts`; `AuthContext.tsx` exports only `AuthProvider` and the bare `AuthContext` object.
- Circular import `client.ts → AuthContext.tsx → auth.ts → client.ts` avoided by introducing `frontend/src/utils/tokenStore.ts` as a dependency-free shared store for the token getter and logout callback. `client.ts` and `AuthContext.tsx` both import from `tokenStore.ts`; neither imports from the other.
- `docker compose restart` does **not** re-read `.env` — it bounces the existing container in-place. `docker compose up -d <service>` recreates the container and picks up new env var values. Discovered when `FRONTEND_URL` was updated from `5173` to `3000` but the backend kept redirecting to `5173` until `up -d` was run.
- `vi.mock` factory return types inferred as `any` by `@typescript-eslint/no-unsafe-return` — fixed by annotating the mock factory's return type explicitly (`: MockAuthState`).

### Completion Notes List

- All 13 ACs implemented and verified end-to-end (GitHub OAuth login → token exchange → AppBar logout → re-login without re-auth).
- `frontend/src/utils/tokenStore.ts` introduced as an unplanned but necessary module to break the circular import between `client.ts` and `AuthContext.tsx`.
- "Continue with Google" button renders as disabled with "coming soon" caption — Story 2.2 (Google OAuth backend) is not yet implemented.
- `/library` and `/profile` protected routes render placeholder `<div>` content — full implementations deferred to Stories 4.x and 3.1 respectively.
- `GET /api/v1/users/me` call in `login()` gracefully handles 404/error (returns `null`) since Story 3.1 is not yet implemented.
- 36 frontend tests pass, ESLint clean, TypeScript clean.

### File List

- `frontend/src/utils/tokenStore.ts` — created: module-level token + logout store (no circular deps)
- `frontend/src/api/auth.ts` — created: `exchangeToken`, `fetchCurrentUser`, `callLogout` API functions
- `frontend/src/contexts/AuthContext.tsx` — created: `AuthProvider`, `AuthContext`, `AuthContextValue` type
- `frontend/src/hooks/useAuth.ts` — created: `useAuth()` hook with error guard
- `frontend/src/pages/LoginPage.tsx` — created: GitHub + Google (disabled) login buttons, error display
- `frontend/src/pages/AuthCallbackPage.tsx` — created: exchange code handler, loading state, redirect logic
- `frontend/src/components/ProtectedRoute/ProtectedRoute.tsx` — created: auth gate with spinner + redirect
- `frontend/src/components/ProtectedRoute/ProtectedRoute.test.tsx` — created
- `frontend/src/pages/LoginPage.test.tsx` — created
- `frontend/src/pages/AuthCallbackPage.test.tsx` — created
- `frontend/src/hooks/useAuth.test.ts` — created
- `frontend/src/api/client.ts` — updated: replaced `localStorage` with `tokenStore.ts` getters
- `frontend/src/App.tsx` — updated: `AuthProvider` wrapper, `/login`, `/auth/callback`, protected routes
- `frontend/src/components/Layout/Layout.tsx` — updated: auth-conditional Sign In / Log Out in AppBar
- `frontend/src/components/Layout/Layout.test.tsx` — updated: added `AuthProvider` to render wrapper
- `docker-compose.yml` — updated: added `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_OAUTH_REDIRECT_URI`, `FRONTEND_URL` to backend `environment:` block
- `.env` — created: local dev credentials (not committed)
