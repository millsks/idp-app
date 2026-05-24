# Story 2.3: Frontend Auth Flow, Token Storage, Route Protection & Logout

Status: ready-for-dev

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

- [ ] Create `frontend/src/contexts/AuthContext.tsx` (AC: 1)
  - [ ] `AuthState` interface and `AuthContextValue` interface per architecture spec
  - [ ] `token` stored in `useRef<string | null>` (NOT `useState`)
  - [ ] `login(exchangeCode)`: calls `POST /api/v1/auth/token/exchange`, on success stores token in ref, fetches user via `GET /api/v1/users/me`, sets `user` state, sets `isAuthenticated=true`
  - [ ] `logout()`: clears token ref, clears user, sets `isAuthenticated=false`
  - [ ] Export `getAuthToken()` module-level getter that returns the current ref value (used by Axios interceptor)
- [ ] Create `frontend/src/hooks/useAuth.ts` (AC: 2)
  - [ ] Wraps `useContext(AuthContext)` with error guard
- [ ] Create `frontend/src/pages/AuthCallbackPage.tsx` (AC: 3, 4)
  - [ ] Reads `exchange_code` from URL search params
  - [ ] Calls `AuthContext.login(exchangeCode)` on mount
  - [ ] Handles success (redirect), error (redirect to /login?error=auth_failed), and loading states
- [ ] Create `frontend/src/components/ProtectedRoute/ProtectedRoute.tsx` (AC: 5, 6)
  - [ ] Uses `useAuth()` — renders `<Outlet />` if authenticated, `<Navigate>` if not
  - [ ] Passes current `location.pathname` as `?redirect=` param
  - [ ] Renders `<LoadingSpinner />` while `isLoading` is true
  - [ ] Write `ProtectedRoute.test.tsx`
- [ ] Create `frontend/src/pages/LoginPage.tsx` (AC: 9, 10)
  - [ ] Two MUI buttons: "Continue with GitHub" → `/api/v1/auth/github`, "Continue with Google" → `/api/v1/auth/google`
  - [ ] Shows error message if `?error=` param is present in URL
  - [ ] NO username/password fields
- [ ] Update `frontend/src/api/client.ts` (AC: 7, 13)
  - [ ] Import `getAuthToken` from `AuthContext`
  - [ ] Request interceptor: `config.headers.Authorization = Bearer ${getAuthToken()}`
  - [ ] 401 response interceptor: call `logout()` from `AuthContext` + redirect to `/login`
- [ ] Update `frontend/src/App.tsx` (AC: 12)
  - [ ] Wrap app in `<AuthContext.Provider>`
  - [ ] Add routes: `/login` → `<LoginPage>`, `/auth/callback` → `<AuthCallbackPage>`
  - [ ] Wrap `/library` and `/profile` routes in `<ProtectedRoute>`
- [ ] Create `frontend/src/api/auth.ts` — API functions for auth endpoints
- [ ] Write tests: `AuthCallbackPage.test.tsx`, `LoginPage.test.tsx`, `useAuth.test.ts`

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

### Debug Log References

### Completion Notes List

### File List
