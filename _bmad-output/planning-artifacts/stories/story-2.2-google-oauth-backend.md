# Story 2.2: Backend OAuth2 — Google Login

Status: ready-for-dev

## Story

As a developer,
I want to log in to idp-app using my Google account,
so that I have a second social login option if I prefer Google over GitHub.

## Acceptance Criteria

1. `GET /api/v1/auth/google` generates a CSRF state token, stores it in Redis under `oauth:state:{token}` with a 5-minute TTL, and redirects the browser to Google's OAuth consent page with scopes `openid email profile`.
2. `GET /api/v1/auth/google/callback?code=&state=` validates the state token (Redis lookup + delete), exchanges the code for a Google access token, and fetches the user's Google profile (sub, email, name, picture).
3. On first login via Google, a new user record is created: `oauth_provider="google"`, `oauth_provider_id` = Google `sub` claim, `username` derived from email prefix, `full_name` from Google `name`, `email`, `avatar_url` from Google `picture`, `hashed_password` = `secrets.token_hex(32)`.
4. On subsequent Google logins, `full_name`, `email`, and `avatar_url` are updated if changed.
5. The same exchange code pattern from Story 2.1 is used: JWT stored in Redis under `auth:exchange:{code}` (30s TTL), browser redirected to `{FRONTEND_URL}/auth/callback?exchange_code={code}`.
6. If a user previously logged in via GitHub with the same email address logs in via Google, a **separate** user record is created (accounts are NOT auto-merged by email in MVP1).
7. Invalid state and provider errors redirect to `{FRONTEND_URL}/login?error=invalid_state` or `login?error=provider_denied` respectively.
8. Structured log entries are emitted for all Google login events (same pattern as Story 2.1 AC-10).
9. New Settings fields are wired: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`.

## Tasks / Subtasks

- [ ] Add new Settings fields to `core/config.py`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` (AC: 9)
  - [ ] Update `.env.example` with Google variables and inline comments
- [ ] Implement Google OAuth endpoints in `api/v1/routes/auth.py` (AC: 1, 2, 3, 4, 5, 6, 7, 8)
  - [ ] `GET /auth/google` — state generation + Redis store + redirect to Google OIDC
  - [ ] `GET /auth/google/callback` — state validation+delete, code exchange via Authlib, profile fetch from Google userinfo endpoint, user upsert, JWT issue, exchange code store, redirect to frontend
  - [ ] Reuse `upsert_oauth_user()` helper extracted from Story 2.1 — pass provider-specific field mapping
  - [ ] AC-6: user lookup ONLY by `(oauth_provider, oauth_provider_id)` — never by email
- [ ] Write tests in `tests/test_auth.py` (AC: 1–8)
  - [ ] Mock Google OIDC token exchange and userinfo responses
  - [ ] Test first-login user creation
  - [ ] Test return-login profile update
  - [ ] Test no-merge behaviour when same email exists under a different provider
  - [ ] Test invalid state and provider error handling

## Dev Notes

- Google uses OIDC (OpenID Connect) on top of OAuth2. Use Authlib's OIDC client. The `sub` field in the ID token is the stable Google user identifier — use this as `oauth_provider_id`, NOT the email.
- Google userinfo endpoint: `https://openid.googleapis.com/v1/userinfo` — returns `sub`, `email`, `name`, `picture`.
- Extract a shared `upsert_oauth_user(db, provider, provider_id, email, full_name, avatar_url)` helper function from Story 2.1's implementation to avoid duplication. This should live in `services/` or inline in `routes/auth.py` as a private function.
- The `username` field for Google users: derive from email prefix (e.g. `user@example.com` → `user`). If that username is taken, append a numeric suffix.
- AC-6 (no email-based merge) is intentional and must be explicitly tested. Two users with the same email but different providers are legitimate separate accounts in MVP1.
- All Story 2.1 infrastructure (migrations, `get_redis()`, Settings, Authlib) is already in place — this story adds only the Google-specific routes and settings.

### Project Structure Notes

- Modify: `backend/src/idp_app/api/v1/routes/auth.py` — add Google OAuth endpoints
- Modify: `backend/src/idp_app/core/config.py` — add Google Settings fields
- Modify: `.env.example` — add Google variables
- Modify: `backend/tests/test_auth.py` — add Google login tests

### References

- Architecture Section 2.1: OAuth2 Flow Architecture — provider field mapping table [Source: _bmad-output/planning-artifacts/architecture.md#21-oauth2-flow-architecture]
- PRD FR-2.2, FR-2.4, FR-2.5 [Source: _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md#Feature-2]
- Story 2.1: GitHub OAuth backend (prerequisite — all infrastructure already in place)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
