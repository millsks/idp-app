---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md
workflowType: architecture
project_name: idp-app
user_name: Millsks
date: 2026-05-24
status: final
---

# Architecture Decision Document — idp-app MVP1

## Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [Core Architectural Decisions](#2-core-architectural-decisions)
   - [OAuth2 Flow Architecture](#21-oauth2-flow-architecture)
   - [Data Architecture](#22-data-architecture)
   - [GitHub Content Service](#23-github-content-service-architecture)
   - [Frontend Auth Architecture](#24-frontend-auth-architecture)
   - [API Surface](#25-api-surface)
   - [Infrastructure & Environment](#26-infrastructure--environment-variables)
3. [Implementation Patterns & Consistency Rules](#3-implementation-patterns--consistency-rules)
4. [Project Structure](#4-project-structure)
5. [Component Boundaries & Integration Points](#5-component-boundaries--integration-points)
6. [Database Schema Changes](#6-database-schema-changes)
7. [Security Checklist](#7-security-checklist)

---

## 1. Technology Stack

All stack decisions are pre-existing in the codebase. No starter template evaluation was required.

| Layer | Technology | Version Constraint |
|-------|-----------|-------------------|
| Backend language | Python | ≥3.12, <3.14 |
| Backend framework | FastAPI | ≥0.115, <1 |
| ORM | SQLAlchemy 2 (async) | ≥2.0, <3 |
| DB driver | asyncpg | ≥0.30 |
| Database | PostgreSQL | via Docker Compose |
| Migrations | Alembic | ≥1.14, <2 |
| Task queue | Celery + Redis | ≥5.4 / ≥5.2 |
| Auth (social) | Authlib | to be added |
| Auth (tokens) | python-jose + passlib[bcrypt] | existing |
| Validation | Pydantic v2 + pydantic-settings | existing |
| Frontend language | TypeScript (strict) | existing |
| Frontend framework | React 19 | existing |
| Build tool | Vite | existing |
| UI components | MUI v6 | existing |
| Server state | TanStack Query | existing |
| Routing | React Router v7 | existing |
| HTTP client | Axios | existing |
| Cache / broker | Redis | via Docker Compose |
| Container | Docker Compose | existing |
| Task runner | pixi | existing |

---

## 2. Core Architectural Decisions

### 2.1 OAuth2 Flow Architecture

**Decision:** Token handoff via short-lived one-time exchange code stored in Redis.

**Rationale:** Keeps the JWT entirely out of redirect URLs (browser history / server logs), cookies, and browser storage during the handoff. The exchange code is single-use with a 30-second TTL.

**Flow:**

```
1. Browser         → GET /api/v1/auth/{provider}
                     FastAPI generates state token (Redis, 5-min TTL)
                     Redirects browser to provider OAuth consent page

2. Provider        → GET /api/v1/auth/{provider}/callback?code=&state=
                     FastAPI validates state (Redis lookup + delete)
                     Exchanges code for access token with provider
                     Fetches user profile from provider API
                     Creates or updates user record in DB
                     Issues idp-app JWT (HS256, 30-min expiry)
                     Stores JWT in Redis as exchange_code → jwt (30-sec TTL)
                     Redirects browser to: {FRONTEND_URL}/auth/callback?exchange_code=XYZ

3. React frontend  → POST /api/v1/auth/token/exchange { exchange_code: "XYZ" }
                     FastAPI: Redis lookup, delete code, return JWT
                     React: store JWT in AuthContext (in-memory, useRef)
                     React Router: redirect to intended destination or /library
```

**CSRF Protection:** State token is a `secrets.token_urlsafe(32)` value stored in Redis under key `oauth:state:{token}` with the target provider as value. Validated and deleted on callback — replay impossible.

**Provider field mapping:**

| idp-app field | GitHub | Google |
|--------------|--------|--------|
| `oauth_provider` | `"github"` | `"google"` |
| `oauth_provider_id` | `user.id` (int→str) | `user.sub` |
| `email` | `user.email` (primary verified) | `user.email` |
| `full_name` | `user.name` | `user.name` |
| `username` | `user.login` | derived from email prefix |
| `avatar_url` | `user.avatar_url` | `user.picture` |
| `hashed_password` | `secrets.token_hex(32)` | `secrets.token_hex(32)` |

**Scopes requested:**

- GitHub: `read:user user:email`
- Google: `openid email profile`

---

### 2.2 Data Architecture

#### Users Table Migration

The existing `users` table requires one Alembic migration adding three columns:

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `oauth_provider` | `VARCHAR(50)` | YES | NULL | `"github"` or `"google"` |
| `oauth_provider_id` | `VARCHAR(255)` | YES | NULL | Provider's stable user ID |
| `avatar_url` | `VARCHAR(500)` | YES | NULL | Provider avatar URL |

`hashed_password` remains `NOT NULL`. OAuth-only users store `secrets.token_hex(32)` — a cryptographically random value that cannot be used to authenticate.

**Unique constraint:** Add composite unique index on `(oauth_provider, oauth_provider_id)` to support user lookup on callback without relying on email (which can change at the provider).

#### No Library Items Table

Library content is **not stored in the application database**. GitHub is the source of truth. Redis is the cache. The `library_items` table does not exist in MVP1.

---

### 2.3 GitHub Content Service Architecture

**Decision:** Celery periodic task populates Redis cache; API reads exclusively from Redis.

**Cache key schema:**

```
library:items                    → Redis Set of all slugs
library:item:{slug}              → Redis Hash (all fields for one item)
library:items:public             → Redis Set of public-flagged slugs
library:last_refresh             → Unix timestamp of last successful sync
library:sync_status              → "ok" | "running" | "error:{message}"
```

**Sync task flow (`tasks/library_sync.py`):**

```python
# Runs every LIBRARY_CACHE_TTL seconds (default 900) via Celery Beat
# Also triggerable via POST /api/v1/library/refresh (superuser only)

1. Set library:sync_status = "running"
2. GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1
   → Extract paths matching /skills/*/SKILL.md and /prompts/*.md
3. For each path, GET /repos/{owner}/{repo}/contents/{path}
   → Decode base64 content
   → Parse YAML frontmatter (title, description, tags, is_public, target_ai)
   → For skills: also fetch README.md for description fallback
   → Derive slug from path (e.g. skills/bmad-code-review/SKILL.md → bmad-code-review)
   → Derive author + last_updated from commit metadata (separate API call per file)
4. Atomic Redis pipeline: delete old keys → write new keys
5. Set library:last_refresh = now(), library:sync_status = "ok"
```

**Rate limit management:** GitHub API allows 5,000 req/hr with a PAT. With a 15-min TTL, worst-case sync frequency is 4/hr. A 1,000-item library requires ~3,000 API calls per sync (tree + content + commit per item). This approaches the limit — implement exponential backoff and log warnings when approaching 80% of rate limit.

**Content frontmatter spec** (canonical, to be documented in content repo):

```yaml
---
title: "Human-readable name"
description: "One-sentence description (used if no README.md)"
tags:
  - tag-one
  - tag-two
target_ai:
  - github-copilot   # canonical values: github-copilot, claude, chatgpt, cursor, gemini
is_public: true       # false = requires authentication to view full content
---
```

---

### 2.4 Frontend Auth Architecture

**AuthContext design:**

```typescript
// src/contexts/AuthContext.tsx
interface AuthState {
  token: string | null;       // stored in useRef — never in state/storage
  user: UserProfile | null;   // { id, email, full_name, avatar_url, oauth_provider }
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (exchangeCode: string) => Promise<void>;
  logout: () => void;
}
```

**Token storage:** `useRef<string | null>` inside `AuthContext`. Survives re-renders within a session; lost on page close/refresh (by design — PRD FR-2.7).

**Axios interceptor** (update existing `src/api/client.ts`):

```typescript
// Request interceptor: reads token from AuthContext via exported getter
apiClient.interceptors.request.use(config => {
  const token = getAuthToken(); // module-level getter set by AuthContext
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor (already exists): 401 → logout() + redirect to /login
```

**Route protection pattern:**

```typescript
// src/components/ProtectedRoute.tsx
// Wraps React Router v7 <Route> — checks isAuthenticated from AuthContext
// If false: <Navigate to={`/login?redirect=${location.pathname}`} replace />
// If isLoading: render <LoadingSpinner />
// If true: render <Outlet />
```

**OAuth callback page** (`src/pages/AuthCallbackPage.tsx`):

```typescript
// Mounted at /auth/callback
// Reads ?exchange_code= from URL
// Calls POST /api/v1/auth/token/exchange
// On success: AuthContext.login(token) → redirect to ?redirect= param or /library
// On failure: redirect to /login?error=auth_failed
```

---

### 2.5 API Surface

All routes under `/api/v1/`. Auth routes in `api/v1/routes/auth.py` (extend existing file). Library routes in new `api/v1/routes/library.py`.

| Method | Path | Auth Required | Description |
|--------|------|--------------|-------------|
| `GET` | `/auth/github` | None | Initiate GitHub OAuth — sets state in Redis, redirects to GitHub |
| `GET` | `/auth/github/callback` | None | GitHub callback — validate state, exchange code, redirect with exchange_code |
| `GET` | `/auth/google` | None | Initiate Google OAuth |
| `GET` | `/auth/google/callback` | None | Google callback |
| `POST` | `/auth/token/exchange` | None | Body: `{exchange_code}` → returns `{access_token, token_type}` |
| `POST` | `/auth/logout` | Bearer | Stateless — client drops token; endpoint returns 200 |
| `GET` | `/users/me` | Bearer | Returns `UserRead` schema for current user |
| `PATCH` | `/users/me` | Bearer | Body: `{full_name}` → returns updated `UserRead` |
| `GET` | `/library/items` | Bearer | Query: `?type=skill\|prompt&tags=&target_ai=&q=&page=&size=` |
| `GET` | `/library/items/{slug}` | Bearer | Single item detail |
| `GET` | `/library/items/public` | None | Public items only — for landing page preview strip |
| `POST` | `/library/refresh` | Bearer + `is_superuser` | Enqueue immediate Celery sync task |

**Standard API response envelope** (all list endpoints):

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "size": 20,
  "pages": 3
}
```

**Standard error envelope:**

```json
{
  "detail": "Human-readable message"
}
```
FastAPI's default `HTTPException` format is used throughout — no custom wrapper.

---

### 2.6 Infrastructure & Environment Variables

No changes to `docker-compose.yml` for MVP1. All required services (postgres, redis, backend, frontend) already exist.

**New variables to add to `.env.example`:**

```env
# ── OAuth: GitHub ──────────────────────────────────────────────────────
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/github/callback

# ── OAuth: Google ──────────────────────────────────────────────────────
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# ── Library Content GitHub Repo ────────────────────────────────────────
GITHUB_CONTENT_TOKEN=          # Fine-grained PAT, contents:read on content repo only
GITHUB_CONTENT_OWNER=          # GitHub username or org owning the content repo
GITHUB_CONTENT_REPO=           # Repository name
GITHUB_CONTENT_BRANCH=main

# ── Library Cache ──────────────────────────────────────────────────────
LIBRARY_CACHE_TTL=900          # Seconds between background syncs (default: 15 min)

# ── Frontend ───────────────────────────────────────────────────────────
FRONTEND_URL=http://localhost:5173   # Used to build OAuth post-login redirect URL
```

These must be added to `idp_app/core/config.py` as `Settings` fields with appropriate validators.

---

## 3. Implementation Patterns & Consistency Rules

These rules exist to ensure all AI agents generate code that works together without conflicts.

### 3.1 Naming Conventions

| Concern | Convention | Example |
|---------|-----------|---------|
| DB table names | `snake_case`, plural | `users`, `oauth_states` |
| DB column names | `snake_case` | `oauth_provider_id`, `avatar_url` |
| DB index names | `ix_{table}_{column}` | `ix_users_oauth_provider_id` |
| API route paths | `kebab-case`, plural nouns | `/library/items`, `/auth/token` |
| API query params | `snake_case` | `?target_ai=claude&page=1` |
| Python files | `snake_case.py` | `library_sync.py`, `auth.py` |
| Python classes | `PascalCase` | `LibraryItem`, `OAuthCallbackParams` |
| Python functions | `snake_case` | `get_library_items`, `sync_library_cache` |
| React component files | `PascalCase.tsx` | `AuthCallbackPage.tsx`, `SkillCard.tsx` |
| React hook files | `use{Name}.ts` | `useAuth.ts`, `useLibraryItems.ts` |
| TypeScript interfaces | `PascalCase` | `LibraryItem`, `AuthState` |
| CSS / MUI sx props | camelCase | `{ marginTop: 2, fontSize: '1rem' }` |
| Environment variables | `SCREAMING_SNAKE_CASE` | `GITHUB_CLIENT_ID` |
| Redis keys | `{domain}:{entity}:{id}` | `library:item:bmad-code-review`, `oauth:state:{token}` |

### 3.2 Backend Patterns

**Dependency injection** — always use `Annotated[T, Depends(f)]` form:
```python
# CORRECT
async def endpoint(db: Annotated[AsyncSession, Depends(get_db)]) -> ...:

# FORBIDDEN
async def endpoint(db: AsyncSession = Depends(get_db)) -> ...:
```

**Current user dependency** — create `get_current_user` in `core/security.py`:
```python
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    # decode JWT → get username → fetch User from DB
    # raise HTTP 401 if invalid/expired
```

**Settings access** — always via `get_settings()`, never `Settings()` directly:
```python
from idp_app.core.config import get_settings
settings = get_settings()
```

**Redis access** — create `get_redis()` dependency in `core/database.py` returning an async Redis client. Always use in routes via `Depends(get_redis)`.

**Route response models** — every endpoint must declare `response_model`. Never return raw dicts.

**HTTP status codes** — always use `status.HTTP_*` constants, never raw integers.

**Error handling** — raise `HTTPException` with a `detail` string. Never let unhandled exceptions reach the client in production.

### 3.3 Frontend Patterns

**API calls** — always through `src/api/client.ts` (`apiClient`). Never use `fetch` directly.

**Query keys** — define as constants in `src/api/queryKeys.ts`:
```typescript
export const QUERY_KEYS = {
  libraryItems: (filters: LibraryFilters) => ['library', 'items', filters],
  libraryItem: (slug: string) => ['library', 'item', slug],
  currentUser: () => ['users', 'me'],
} as const;
```

**Auth reads** — always read `isAuthenticated`, `user`, `token` from `useAuth()` hook (wraps `AuthContext`). Never read AuthContext directly in components.

**Protected routes** — wrap with `<ProtectedRoute>` in `App.tsx`. Never implement auth checks inline in pages.

**Loading states** — use TanStack Query `isLoading` / `isPending`. Never implement custom loading state for server data.

**Error boundaries** — wrap each major page section. Never let unhandled React errors crash the full app.

**Component exports** — named exports only. No default exports for components.

### 3.4 Celery Task Patterns

**Task naming** — `{module}.{verb}_{noun}`:
```python
@celery_app.task(name="library.sync_content")
def sync_library_content() -> dict:
```

**Task return values** — always return a dict with `status` key:
```python
return {"status": "ok", "items_synced": 42}
```

**Error handling in tasks** — catch all exceptions, log, set `library:sync_status = "error:{msg}"`, re-raise so Celery marks task as failed.

**Beat schedule** — defined in `tasks/worker.py`, not in `celery.conf` directly:
```python
celery_app.conf.beat_schedule = {
    "sync-library-content": {
        "task": "library.sync_content",
        "schedule": settings.LIBRARY_CACHE_TTL,
    },
}
```

---

## 4. Project Structure

Changes and additions to the existing codebase for MVP1:

```
backend/
  src/idp_app/
    api/v1/routes/
      auth.py          ← MODIFY: add OAuth2 + token exchange endpoints
      library.py       ← NEW: library list, detail, refresh endpoints
      users.py         ← MODIFY: add /me GET and PATCH endpoints
    core/
      config.py        ← MODIFY: add OAuth + GitHub content settings fields
      database.py      ← MODIFY: add get_redis() async dependency
      security.py      ← MODIFY: add get_current_user() dependency
    models/
      user.py          ← MODIFY: add oauth_provider, oauth_provider_id, avatar_url
    schemas/
      user.py          ← MODIFY: add UserMe, UserMeUpdate response schemas
      library.py       ← NEW: LibraryItem, LibraryItemList, LibraryFilters schemas
    services/
      github_content.py ← NEW: GitHub API client for fetching content repo files
    tasks/
      worker.py        ← MODIFY: add Celery Beat schedule for library sync
      library_sync.py  ← NEW: sync_library_content() Celery task
    alembic/versions/
      {date}_add_oauth_fields_to_users.py  ← NEW: migration

frontend/src/
  api/
    client.ts          ← MODIFY: wire AuthContext token getter into request interceptor
    queryKeys.ts       ← NEW: centralised TanStack Query key constants
    library.ts         ← NEW: API functions for library endpoints
    auth.ts            ← NEW: API functions for auth endpoints
    users.ts           ← NEW: API functions for /users/me
  contexts/
    AuthContext.tsx    ← NEW: in-memory token + user state
  hooks/
    useAuth.ts         ← NEW: consumer hook wrapping AuthContext
    useLibraryItems.ts ← NEW: TanStack Query hook for library list
    useLibraryItem.ts  ← NEW: TanStack Query hook for single item
  components/
    ProtectedRoute/
      ProtectedRoute.tsx    ← NEW: auth guard wrapper for React Router
      ProtectedRoute.test.tsx
    Layout/
      Layout.tsx        ← MODIFY: add auth-aware nav (login/logout/avatar)
    LibraryItem/
      SkillCard.tsx     ← NEW: card for library list view
      SkillCard.test.tsx
      ItemDetail.tsx    ← NEW: full detail view with copy-to-clipboard
      ItemDetail.test.tsx
    LandingPreview/
      PublicPreviewStrip.tsx  ← NEW: public items preview on landing page
  pages/
    LoginPage.tsx          ← NEW: social login buttons
    AuthCallbackPage.tsx   ← NEW: exchange_code → token → redirect
    LibraryPage.tsx        ← NEW: authenticated library browse/search
    ProfilePage.tsx        ← NEW: user profile view + display name edit
    HomePage.tsx           ← MODIFY: add PublicPreviewStrip
  App.tsx                  ← MODIFY: add new routes + ProtectedRoute wrapping
```

---

## 5. Component Boundaries & Integration Points

```
┌─────────────────────────────────────────────────────┐
│                   React SPA (nginx)                  │
│                                                     │
│  Public routes     │  Protected routes              │
│  /                 │  /library                      │
│  /login            │  /profile                      │
│  /auth/callback    │                                │
│                    │  AuthContext (in-memory JWT)    │
│  ──────────────────┼────────────────────────────    │
│        Axios apiClient (JWT Bearer header)           │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / REST
┌──────────────────────▼──────────────────────────────┐
│                FastAPI (port 8000)                   │
│                                                     │
│  /api/v1/auth/*    │  /api/v1/users/me              │
│  /api/v1/library/* │  /api/v1/health                │
│                    │                                │
│  ── Depends(get_current_user) ──────────────────    │
│  ── Depends(get_db)  ─── AsyncSession ──────────    │
│  ── Depends(get_redis) ─ Redis client ──────────    │
└────────┬────────────────────┬───────────────────────┘
         │                    │
┌────────▼────────┐  ┌────────▼────────────────────────┐
│   PostgreSQL    │  │            Redis                 │
│                 │  │                                  │
│  users table    │  │  oauth:state:{token}  (5m TTL)   │
│  (+ 3 new cols) │  │  auth:exchange:{code} (30s TTL)  │
│                 │  │  library:item:{slug}  (no TTL)   │
└─────────────────┘  │  library:items        (no TTL)   │
                     │  library:last_refresh             │
                     └─────────┬───────────────────────┘
                               │ populated by
                     ┌─────────▼───────────────────────┐
                     │    Celery Worker + Beat          │
                     │                                  │
                     │  library.sync_content            │
                     │  (every LIBRARY_CACHE_TTL secs)  │
                     └─────────┬───────────────────────┘
                               │ GitHub API (PAT)
                     ┌─────────▼───────────────────────┐
                     │   GitHub Content Repository      │
                     │                                  │
                     │  /skills/{slug}/SKILL.md         │
                     │  /skills/{slug}/README.md        │
                     │  /prompts/{slug}.md              │
                     └─────────────────────────────────┘
```

---

## 6. Database Schema Changes

Single Alembic migration required. Generate with:
```bash
pixi run backend-migration -m "add oauth fields to users"
```

**Migration content (autogenerate will produce):**
```python
def upgrade() -> None:
    op.add_column("users", sa.Column("oauth_provider", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("oauth_provider_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(500), nullable=True))
    op.create_index("ix_users_oauth_provider_id",
                    "users", ["oauth_provider", "oauth_provider_id"], unique=True)

def downgrade() -> None:
    op.drop_index("ix_users_oauth_provider_id", table_name="users")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "oauth_provider_id")
    op.drop_column("users", "oauth_provider")
```

**Updated SQLAlchemy model (`models/user.py`) additions:**
```python
oauth_provider:    Mapped[str | None] = mapped_column(String(50),  nullable=True)
oauth_provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
avatar_url:        Mapped[str | None] = mapped_column(String(500), nullable=True)
```

---

## 7. Security Checklist

| # | Control | Implementation |
|---|---------|---------------|
| 1 | OAuth CSRF | `secrets.token_urlsafe(32)` state in Redis; validated + deleted on callback |
| 2 | Exchange code single-use | Redis key deleted immediately on `POST /auth/token/exchange` |
| 3 | JWT in-memory only | `useRef` in AuthContext — not localStorage/sessionStorage/cookie |
| 4 | JWT expiry | 30 minutes, HS256 — existing `create_access_token` implementation |
| 5 | Secrets in env only | `SECRET_KEY`, `*_CLIENT_SECRET`, `GITHUB_CONTENT_TOKEN` — never committed |
| 6 | OAuth-only password | `secrets.token_hex(32)` stored — cannot authenticate, satisfies NOT NULL |
| 7 | GitHub PAT scope | `contents:read` on content repo only — minimum privilege |
| 8 | CORS restriction | `ALLOWED_ORIGINS` restricted to frontend origin in production |
| 9 | Protected endpoint gate | All non-public endpoints require valid JWT via `get_current_user` dependency |
| 10 | Public library items | `is_public` flag checked in `/library/items/public` — no auth bypass for private items |
| 11 | Superuser gate | `/library/refresh` checks `current_user.is_superuser` — raises HTTP 403 if false |
| 12 | No secrets in logs | OAuth tokens, JWTs, and PATs must never appear in structured log entries |
