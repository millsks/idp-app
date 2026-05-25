# Deferred Work

## Deferred from: code review of 0-1-upgrade-nodejs-24 (2026-05-24)

- **Mutable `node:24-alpine` Docker tag — no image digest pin** [`docker/frontend/Dockerfile:7`]: The builder stage uses a floating tag. Consider pinning to a digest (e.g., `node:24-alpine@sha256:...`) for reproducible builds. Pre-existing pattern — `node:22-alpine` was also unpinned.
- **`>=24,<25` upper bound requires manual bump when Node.js 26 LTS arrives** [`pixi.toml:18`]: When Node.js 26 enters Active LTS (expected ~Oct 2028), the constraint will need updating to `>=26,<27` (or `>=24,<27` for a wider window). Intentional by design, consistent with `python = ">=3.12,<3.14"` convention.

## Deferred from: code review of story-2.1-github-oauth-backend (2026-05-24)

- **Email uniqueness not guarded on first OAuth login** [`backend/src/idp_app/api/v1/routes/auth.py` — first-login branch]: If a password account already owns the GitHub-returned email, `db.flush()` raises `IntegrityError` → 500. The fix (check by email before `db.add(user)`, or link the OAuth identity to the existing account) requires an integration test with a real PostgreSQL instance; unit-test harness (SQLite + FakeRedis) cannot reliably cover the IntegrityError path. Implement in a dedicated story alongside integration test infrastructure.
- **JWT stored in Redis behind exchange code** [`backend/src/idp_app/api/v1/routes/auth.py:244`]: Live JWT leaks if exchange code is intercepted (browser history, referrer header); consider storing only user ID or session reference and issuing JWT at exchange time. Architectural trade-off — accepted design for MVP.
- **Non-atomic GET+DELETE on `/token/exchange`** [`backend/src/idp_app/api/v1/routes/auth.py:261`]: Two concurrent requests with the same code could both pass the `get` check before either deletes the key; replace with Redis `GETDEL` command for atomic single-use guarantee. Low practical risk with 256-bit tokens.
- **Race condition: state deleted before user upsert commits** [`backend/src/idp_app/api/v1/routes/auth.py:144`]: If `db.flush()` fails after state deletion, the state is irrevocably consumed and the user receives a `provider_denied` redirect with no retry path. Requires retry-design decision.
- **Token exchange endpoint not rate-limited** [`backend/src/idp_app/api/v1/routes/auth.py:255`]: No throttle on exchange code guesses; address at API gateway/middleware layer rather than in application code.
- **`FakeRedis` does not enforce TTL expiry** [`backend/tests/conftest.py:30`]: Expiry-based failure modes (OAuth state timeout after 300 s, exchange code timeout after 30 s) are untested. Upgrade to `fakeredis` PyPI package (supports TTL) or implement timer-based expiry in `FakeRedis`.
- **Username-collision fallback branch untested** [`backend/src/idp_app/api/v1/routes/auth.py:202`]: No test creates a conflicting local username then triggers GitHub first-login. Add a test that pre-creates `User(username="octocat")` then runs the callback with `login="octocat"` and asserts `username == "github_<id>"`.
- **`GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` default to empty string** [`backend/src/idp_app/core/config.py:84`]: App starts and OAuth routes are reachable even without credentials configured; OAuth exchange silently fails at runtime. Consider adding a validator that warns (or raises if `ENVIRONMENT == "production"`) when these fields are empty.

## Deferred from: code review of story-4.2-library-browse-search-filter (2026-05-24)

- **Full dataset loaded into memory before filtering** [`backend/src/idp_app/api/v1/routes/library.py`]: All library items are fetched from Redis and decoded before any filtering is applied. Explicitly accepted in Dev Notes as viable for MVP1 (≤1,000 items). Should be revisited if the catalogue grows significantly.

## Deferred from: story-2.2-google-oauth-backend manual verification (2026-05-24)

- **Google Cloud project not yet available for OAuth verification** [`.env` / Google Cloud Console]: End-to-end Google login cannot be verified locally until a Google Cloud project is created and OAuth web credentials are provisioned (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) with redirect URI `http://localhost:8000/api/v1/auth/google/callback`. Once available, set `FRONTEND_URL` to the active dev port and re-run manual login validation.
