---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md
  - _bmad-output/planning-artifacts/architecture.md
---

# idp-app - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for idp-app MVP1, decomposing requirements from the PRD and Architecture into implementable, sprint-ready stories.

---

## Requirements Inventory

### Functional Requirements

**Feature 1 — Public Landing Page**
- FR-1.1: The landing page SHALL be accessible to unauthenticated users without any login prompt.
- FR-1.2: The landing page SHALL communicate the portal's purpose in a headline and supporting copy.
- FR-1.3: The landing page SHALL surface the planned capability pillars as visual cards (Skills & Prompts Library, Software Marketplace, Developer Utilities, Application Accelerators, Vulnerability Library) — even if not all are live in MVP1.
- FR-1.4: The landing page SHALL include a clear call-to-action to sign in or register.
- FR-1.5: The landing page SHALL include links to the project's GitHub repository (open-source disclosure).
- FR-1.6: A preview strip of recent or featured public skills/prompts SHALL be visible on the landing page. Clicking an item shows title and description only; full content requires authentication.

**Feature 2 — Authentication & Social Login**
- FR-2.1: The system SHALL support user registration and login via GitHub OAuth2.
- FR-2.2: The system SHALL support user registration and login via Google OAuth2.
- FR-2.3: OAuth2 flows SHALL be implemented using Authlib directly against provider APIs (no hosted identity service).
- FR-2.4: On first successful OAuth2 login, the system SHALL create a new user record populated with provider profile data (display name, email, avatar URL).
- FR-2.5: On subsequent logins, the system SHALL update the user record with any changed profile fields from the provider.
- FR-2.6: A user authenticated via social login SHALL receive a short-lived JWT access token (HS256, 30-minute expiry).
- FR-2.7: JWT access tokens SHALL be stored in-memory only on the frontend (React context). Tokens SHALL NOT be written to localStorage or sessionStorage.
- FR-2.7a: On page refresh, the user SHALL be required to re-authenticate. Silent re-auth is out of scope for MVP1.
- FR-2.8: The login page SHALL present both social login buttons ("Continue with GitHub", "Continue with Google") prominently. Username/password form SHALL NOT be exposed in MVP1 UI.
- FR-2.9: The system SHALL handle OAuth2 provider errors gracefully and return the user to the login page with a clear error message.
- FR-2.10: Logging out SHALL invalidate the frontend token and redirect the user to the public landing page.

**Feature 3 — User Profile**
- FR-3.1: An authenticated user SHALL be able to access a /profile page that is protected from unauthenticated access.
- FR-3.2: The profile page SHALL display: display name, email address, provider avatar image, account creation date, and OAuth2 provider identity (GitHub / Google).
- FR-3.3: The user SHALL be able to update their display name on the profile page.
- FR-3.4: Email address SHALL be read-only on the profile page (sourced from OAuth provider).
- FR-3.5: The backend SHALL expose a GET /api/v1/users/me endpoint requiring a valid JWT Bearer token.
- FR-3.6: The backend SHALL expose a PATCH /api/v1/users/me endpoint for display name updates, requiring a valid JWT Bearer token.

**Feature 4 — Authenticated Route Protection**
- FR-4.1: All non-public routes SHALL redirect unauthenticated users to the login page.
- FR-4.2: After successful login, the user SHALL be redirected to the page they originally attempted to access (redirect-on-login pattern) or to /library if no prior destination.
- FR-4.3: The frontend router SHALL implement route-level authentication guards.
- FR-4.4: The API SHALL return HTTP 401 for protected endpoints accessed without a valid token. The frontend JWT interceptor SHALL clear the token and redirect to /login.

**Feature 5 — AI Skills & Prompts Library**
- FR-5.1: The library SHALL be accessible only to authenticated users.
- FR-5.2: The library SHALL contain two distinct content types — Skills and Prompts — unified under a single content_type tag for filtering and API access.
- FR-5.3: All library content SHALL be stored in and retrieved from a dedicated GitHub content repository. Owner, repo, and branch SHALL be configurable via environment variables.
- FR-5.4: Library content SHALL be loaded from GitHub at application startup and cached in Redis with a configurable TTL (default: 15 minutes). A superuser cache invalidation endpoint SHALL allow forced refresh without restarting.
- FR-5.5: Each library item SHALL include: content_type, title, description, category/tags, content (raw Markdown), is_public flag, author (GitHub handle), last updated date (from Git commit), and target AI assistant(s).
- FR-5.6: The library page SHALL display skills and prompts in a searchable, filterable list/grid.
- FR-5.7: Search SHALL operate across title, description, tags, and content (full-text).
- FR-5.8: Filters SHALL include: content type (Skill / Prompt), category/tags, and target AI assistant.
- FR-5.9: Each item SHALL have a detail view displaying full rendered Markdown content, metadata, and a "Copy to clipboard" action.
- FR-5.10: A "View on GitHub" link SHALL be present on each item detail view, pointing to the source file in the content repository.
- FR-5.11: The library SHALL include seed content on first launch sourced from the dedicated GitHub content repository.
- FR-5.12: Skills SHALL be sourced from /skills/{slug}/SKILL.md. The /skills/{slug}/README.md SHALL populate the description field when present.
- FR-5.13: Prompts SHALL be sourced from /prompts/{slug}.md in the content repository.

---

### Non-Functional Requirements

**Security**
- NFR-4.1.1: OAuth2 state parameter SHALL be validated on callback to prevent CSRF.
- NFR-4.1.2: JWT tokens SHALL use HS256 and expire in 30 minutes.
- NFR-4.1.3: SECRET_KEY, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GITHUB_CONTENT_TOKEN SHALL be supplied via environment variables and NEVER committed.
- NFR-4.1.4: The hashed_password column SHALL store a cryptographically random unusable hash for OAuth-only accounts (NOT NULL constraint maintained).
- NFR-4.1.5: All API responses SHALL include appropriate CORS headers; ALLOWED_ORIGINS restricted to frontend origin in production.
- NFR-4.1.6: GitHub API calls for content retrieval SHALL use a scoped PAT with contents:read permission only.

**Performance**
- NFR-4.2.1: Library list page first contentful paint SHALL be under 2 seconds on standard broadband.
- NFR-4.2.2: GitHub content cache SHALL ensure no user-facing request waits on a live GitHub API call during a cache-hit.
- NFR-4.2.3: Search results SHALL return within 500ms for a library of up to 1,000 items.

**Accessibility**
- NFR-4.3.1: All pages SHALL meet WCAG 2.1 AA contrast requirements.
- NFR-4.3.2: All interactive elements SHALL be keyboard-navigable.

**Observability**
- NFR-4.4.1: Structured log entries SHALL be emitted for login events (provider, success/failure), library cache refresh events, and API errors.
- NFR-4.4.2: The existing /api/v1/health endpoint SHALL remain functional and reflect database connectivity status.

**Compatibility**
- NFR-4.5.1: The frontend SHALL support the latest two stable versions of Chrome, Firefox, Safari, and Edge.
- NFR-4.5.2: The application SHALL be deployable via the existing Docker Compose configuration.

---

### Additional Requirements (from Architecture)

- ARCH-1: OAuth2 token handoff MUST use a short-lived one-time exchange code stored in Redis (30s TTL, single-use) — JWT must never appear in redirect URLs, cookies, or browser storage during handoff.
- ARCH-2: DB migration required: add oauth_provider (VARCHAR 50), oauth_provider_id (VARCHAR 255), avatar_url (VARCHAR 500) columns to users table, plus composite unique index on (oauth_provider, oauth_provider_id).
- ARCH-3: hashed_password for OAuth-only users = secrets.token_hex(32); column stays NOT NULL.
- ARCH-4: GitHub content sync implemented as a Celery Beat periodic task (library.sync_content) running every LIBRARY_CACHE_TTL seconds.
- ARCH-5: GitHub content cache uses structured Redis keys: library:item:{slug}, library:items (Set), library:items:public (Set), library:last_refresh, library:sync_status.
- ARCH-6: Content frontmatter MUST be parsed from each SKILL.md / prompt .md file (title, description, tags, is_public, target_ai fields).
- ARCH-7: GitHub API rate limit management required — exponential backoff, warning at 80% of 5000 req/hr limit.
- ARCH-8: New environment variables required: GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_OAUTH_REDIRECT_URI, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_OAUTH_REDIRECT_URI, GITHUB_CONTENT_TOKEN, GITHUB_CONTENT_OWNER, GITHUB_CONTENT_REPO, GITHUB_CONTENT_BRANCH, LIBRARY_CACHE_TTL, FRONTEND_URL.
- ARCH-9: All backend routes MUST use Annotated[T, Depends(f)] form for dependency injection — never positional Depends().
- ARCH-10: get_current_user() dependency MUST be added to core/security.py for JWT-protected endpoints.
- ARCH-11: get_redis() async dependency MUST be added to core/database.py.
- ARCH-12: All list API endpoints MUST return standard envelope: {items, total, page, size, pages}.
- ARCH-13: Superuser cache refresh endpoint: POST /api/v1/library/refresh — checks current_user.is_superuser, raises HTTP 403 if false.
- ARCH-14: Public library preview endpoint: GET /api/v1/library/items/public — no auth required, returns is_public=true items only.

---

### UX Design Requirements

No UX design document exists for MVP1. UX patterns are derived from the architecture and PRD user journeys. Stories will define acceptance criteria based on those patterns.

---

### FR Coverage Map

| Requirement | Epic | Story |
|-------------|------|-------|
| FR-1.1 – FR-1.5 | Epic 1 | Story 1.1 |
| FR-1.6, ARCH-14 | Epic 1 | Story 1.2 |
| FR-2.1 – FR-2.6, FR-2.9, ARCH-1, ARCH-2, ARCH-3, NFR-4.1.1 – NFR-4.1.4 | Epic 2 | Story 2.1 |
| FR-2.4 – FR-2.5, FR-2.1 – FR-2.2 (Google) | Epic 2 | Story 2.2 |
| FR-2.7, FR-2.7a, FR-2.8, FR-2.10, FR-4.1 – FR-4.4, ARCH-10, ARCH-11 | Epic 2 | Story 2.3 |
| FR-3.1 – FR-3.6, ARCH-10 | Epic 3 | Story 3.1 |
| FR-5.3, FR-5.4, FR-5.5, FR-5.12, FR-5.13, ARCH-4 – ARCH-8 | Epic 4 | Story 4.1 |
| FR-5.1, FR-5.2, FR-5.6 – FR-5.8, ARCH-12 | Epic 4 | Story 4.2 |
| FR-5.9, FR-5.10, FR-5.11 | Epic 4 | Story 4.3 |
| NFR-4.1.1 – NFR-4.1.6 | Cross-cutting | All epics |
| NFR-4.2.1 – NFR-4.2.3 | Epic 4 | Stories 4.1 – 4.3 |
| NFR-4.3.1 – NFR-4.3.2 | All epics | All UI stories |
| NFR-4.4.1 – NFR-4.4.2 | Epic 2, Epic 4 | Stories 2.1, 4.1 |
| NFR-4.5.1 – NFR-4.5.2 | Cross-cutting | Final milestone |

---

## Epic List

1. **Epic 1 — Public Landing Page** — Public-facing portal shell with capability showcase and preview strip
2. **Epic 2 — Authentication & Identity** — Social login (GitHub + Google), JWT auth flow, route protection, and user session
3. **Epic 3 — User Profile** — Authenticated profile page with read/update capabilities
4. **Epic 4 — AI Skills & Prompts Library** — GitHub-backed content sync, library browse/search, and item detail views

---

## Epic 1: Public Landing Page

**Goal:** Deliver a compelling public-facing portal home page that communicates the product vision, showcases the capability roadmap, and drives unauthenticated visitors toward sign-up. This is the first thing any visitor sees and must convert curiosity into registration intent.

### Story 1.1: Public Landing Page Shell

As a public visitor,
I want to see a clear, well-designed landing page that explains what idp-app is and what it offers,
So that I can understand the value proposition and decide whether to sign up.

**Acceptance Criteria:**

**Given** I visit the portal root URL (/) without being logged in
**When** the page loads
**Then** I see a headline and supporting copy describing the portal
**And** I see visual cards for each planned capability pillar: Skills & Prompts Library, Software Marketplace, Developer Utilities, Application Accelerators, Vulnerability Library
**And** pillar cards for unbuilt features are visually marked as "Coming Soon"
**And** I see a prominent "Sign In" call-to-action button
**And** I see a link to the project's GitHub repository
**And** I am NOT prompted to log in or shown an auth modal unprompted
**And** the page passes WCAG 2.1 AA contrast requirements
**And** all interactive elements are keyboard-navigable

**Given** I am already authenticated
**When** I visit /
**Then** the "Sign In" CTA is replaced with a link to the library or my profile

---

### Story 1.2: Public Preview Strip

As a public visitor,
I want to see a preview of real skills and prompts on the landing page,
So that I can evaluate the library's content quality before committing to sign up.

**Acceptance Criteria:**

**Given** the library cache has been populated with at least one public item (is_public=true)
**When** I visit the landing page unauthenticated
**Then** I see a preview strip of up to 6 featured public library items
**And** each preview card shows: title, description, content_type badge (Skill / Prompt), and tags
**And** item content/full-text is NOT displayed in the preview strip

**Given** I click a preview card
**When** I am unauthenticated
**Then** I see the item title and description only
**And** I see a "Sign in to view full content" prompt or CTA
**And** I am NOT shown the full Markdown content

**Given** the library cache is empty or unavailable
**When** I visit the landing page
**Then** the preview strip is hidden or shows a placeholder message
**And** the rest of the landing page renders correctly

**Given** the GET /api/v1/library/items/public endpoint is called
**When** no auth token is present
**Then** the endpoint returns HTTP 200 with a list of public items (no 401)

---

## Epic 2: Authentication & Identity

**Goal:** Implement the complete OAuth2 social login flow for GitHub and Google providers using Authlib, with secure JWT issuance, in-memory token storage on the frontend, route protection, and logout. This epic establishes all authentication infrastructure that downstream epics depend on.

### Story 2.1: Backend OAuth2 — GitHub Login

As a developer,
I want to log in to idp-app using my existing GitHub account,
So that I don't have to create and remember another username/password.

**Acceptance Criteria:**

**Given** I click "Continue with GitHub" on the login page
**When** I am redirected back from GitHub after authorising the app
**Then** a new user record is created in the database if this is my first login
**And** the user record contains my GitHub display name, email, and avatar URL
**And** my oauth_provider is set to "github" and oauth_provider_id to my GitHub user ID
**And** my hashed_password is set to a secrets.token_hex(32) unusable hash

**Given** I have previously logged in via GitHub and my display name changed on GitHub
**When** I log in again
**Then** my user record is updated with the new display name

**Given** the backend initiates an OAuth2 flow
**When** GET /api/v1/auth/github is called
**Then** a CSRF state token (secrets.token_urlsafe(32)) is stored in Redis with a 5-minute TTL under key oauth:state:{token}
**And** the browser is redirected to GitHub's OAuth consent page with the state parameter

**Given** GitHub redirects to /api/v1/auth/github/callback
**When** the state parameter is valid (exists in Redis)
**Then** the state key is deleted from Redis (single-use, replay impossible)
**And** the code is exchanged for a GitHub access token
**And** the user's GitHub profile is fetched (scopes: read:user user:email)
**And** an idp-app JWT (HS256, 30-min expiry) is issued
**And** the JWT is stored in Redis under key auth:exchange:{code} with a 30-second TTL
**And** the browser is redirected to {FRONTEND_URL}/auth/callback?exchange_code={code}

**Given** the state parameter is invalid or missing on callback
**When** the callback endpoint is called
**Then** the user is redirected to /login with an error query parameter
**And** no user record is created or modified

**Given** a structured log
**When** a login succeeds or fails
**Then** an entry is logged with: provider, success/failure, user id (on success), error type (on failure) — no tokens or secrets in log

---

### Story 2.2: Backend OAuth2 — Google Login

As a developer,
I want to log in to idp-app using my Google account,
So that I have a second social login option if I prefer Google over GitHub.

**Acceptance Criteria:**

**Given** I click "Continue with Google" on the login page
**When** I am redirected back from Google after authorising the app
**Then** a new user record is created using my Google profile (scopes: openid email profile)
**And** my oauth_provider is set to "google" and oauth_provider_id to my Google sub claim
**And** my username is derived from my email prefix if not otherwise set
**And** the flow follows the same exchange code pattern as the GitHub flow (Story 2.1 ACs apply)

**Given** a user who previously logged in via GitHub tries to log in via Google with the same email
**When** the Google callback is processed
**Then** a SEPARATE user record is created (accounts are NOT auto-merged by email in MVP1)

**Given** GET /api/v1/auth/google is called
**Then** the correct Google OAuth consent URL is generated with the state parameter
**And** scopes requested are: openid email profile

---

### Story 2.3: Frontend Auth Flow, Token Storage, Route Protection & Logout

As a developer,
I want the frontend to handle the OAuth callback, store my token securely, protect private pages, and let me log out cleanly,
So that my session is secure and the app behaves correctly whether I am authenticated or not.

**Acceptance Criteria:**

**Given** the browser lands on /auth/callback?exchange_code=XYZ
**When** AuthCallbackPage mounts
**Then** it calls POST /api/v1/auth/token/exchange with the exchange code
**And** on success, the JWT is stored in AuthContext using useRef (in-memory only)
**And** the exchange code is never stored in any browser storage or logged
**And** the user is redirected to the original intended route (via ?redirect= param) or /library

**Given** the exchange code has expired (>30 seconds) or was already used
**When** POST /api/v1/auth/token/exchange is called
**Then** the API returns HTTP 400 or 401
**And** AuthCallbackPage redirects to /login?error=auth_failed

**Given** I am unauthenticated and navigate directly to /library or /profile
**When** ProtectedRoute evaluates authentication state
**Then** I am redirected to /login?redirect=/library (or /profile)
**And** after successful login I am sent to /library (or /profile)

**Given** I am authenticated
**When** my JWT expires (30 minutes)
**Then** the next API call returns HTTP 401
**And** the Axios interceptor clears the AuthContext token
**And** I am redirected to /login

**Given** I refresh the browser page
**When** the app reinitialises
**Then** the AuthContext token is null (in-memory token is lost)
**And** I am treated as unauthenticated and redirected to /login if I try to access a protected route

**Given** I click "Log Out"
**When** the logout action is triggered
**Then** the AuthContext token and user are cleared
**And** I am redirected to the public landing page (/)
**And** POST /api/v1/auth/logout is called (returns 200, stateless operation)

**Given** the login page renders
**Then** I see "Continue with GitHub" and "Continue with Google" buttons
**And** NO username/password form is present

---

## Epic 3: User Profile

**Goal:** Give authenticated users a profile page where they can view their identity information sourced from their OAuth provider and update their display name. Establishes the /users/me backend endpoints needed by both the profile UI and any future feature that needs the current user.

### Story 3.1: User Profile Page & /users/me Endpoints

As an authenticated developer,
I want to see and manage my profile information,
So that I can verify my identity details and personalise my display name on the portal.

**Acceptance Criteria:**

**Given** I am authenticated and navigate to /profile
**When** the page loads
**Then** I see my display name, email address, provider avatar image, account creation date, and OAuth2 provider badge (GitHub or Google)
**And** the email field is read-only with a note that it is sourced from the OAuth provider
**And** the page is NOT accessible if I am not authenticated (redirects to /login)

**Given** I change my display name in the text field and click Save
**When** PATCH /api/v1/users/me is called with the new full_name value
**Then** the profile page updates immediately with the new display name
**And** the API returns the updated UserRead schema
**And** the change persists on page refresh (stored in DB)

**Given** I submit a blank display name
**When** PATCH /api/v1/users/me is called
**Then** the API returns HTTP 422 with a validation error
**And** the profile page shows an inline error message

**Given** GET /api/v1/users/me is called with a valid JWT Bearer token
**Then** the response contains: id, email, full_name, avatar_url, oauth_provider, is_active, is_superuser, created_at

**Given** GET /api/v1/users/me is called without a token or with an expired token
**Then** the response is HTTP 401

**Given** PATCH /api/v1/users/me is called without a token
**Then** the response is HTTP 401

**Given** PATCH /api/v1/users/me is called by a superuser changing their own name
**Then** is_superuser status is NOT affected by the update

---

## Epic 4: AI Skills & Prompts Library

**Goal:** Implement the full library feature: a Celery-powered GitHub content sync service that populates a Redis cache, a set of authenticated API endpoints for browsing/searching/filtering items, a public preview endpoint, and the authenticated library UI with search, filter, and item detail views including copy-to-clipboard.

### Story 4.1: GitHub Content Sync Service

As a portal administrator,
I want library content to be automatically synced from the GitHub content repository and cached in Redis,
So that the library always reflects the latest published skills and prompts without manual intervention.

**Acceptance Criteria:**

**Given** the Celery Beat scheduler is running
**When** the library.sync_content task fires (at startup and every LIBRARY_CACHE_TTL seconds)
**Then** it fetches the repository file tree from the GitHub API using GITHUB_CONTENT_TOKEN
**And** it identifies all /skills/{slug}/SKILL.md and /prompts/{slug}.md paths
**And** it fetches and decodes file contents
**And** it parses YAML frontmatter from each file (title, description, tags, is_public, target_ai)
**And** for skills, it fetches /skills/{slug}/README.md for the description field if present
**And** it derives author and last_updated from the file's most recent commit metadata
**And** it writes each item atomically to Redis: library:item:{slug} as a Hash, slug added to library:items Set, public items added to library:items:public Set
**And** it sets library:last_refresh to the current Unix timestamp
**And** it sets library:sync_status to "ok"

**Given** the GitHub API returns an error during sync
**When** the task encounters the error
**Then** it retries with exponential backoff
**And** it sets library:sync_status to "error:{message}"
**And** it logs a structured error entry
**And** the existing cached items are NOT deleted (stale cache preserved on error)

**Given** the GitHub API rate limit is approaching 80% of 5,000 req/hr
**When** the sync task detects this threshold
**Then** it logs a structured warning entry with the current rate limit counter

**Given** a superuser calls POST /api/v1/library/refresh
**When** the endpoint is hit with a valid superuser JWT
**Then** an immediate library.sync_content task is enqueued via Celery
**And** the endpoint returns HTTP 202 Accepted

**Given** a non-superuser calls POST /api/v1/library/refresh
**Then** the endpoint returns HTTP 403 Forbidden

**Given** the new environment variables (GITHUB_CONTENT_TOKEN, GITHUB_CONTENT_OWNER, GITHUB_CONTENT_REPO, GITHUB_CONTENT_BRANCH, LIBRARY_CACHE_TTL, FRONTEND_URL, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET) are added to Settings
**Then** the application starts without errors when all required vars are set
**And** .env.example is updated with all new variables and inline documentation comments

---

### Story 4.2: Library Browse, Search & Filter

As an authenticated developer,
I want to browse, search, and filter the library of skills and prompts,
So that I can quickly find the content most relevant to my current task.

**Acceptance Criteria:**

**Given** I am authenticated and navigate to /library
**When** the page loads
**Then** I see a list/grid of library items loaded from GET /api/v1/library/items
**And** each card shows: title, description snippet, content_type badge, tags, and target AI assistants
**And** the page first contentful paint completes in under 2 seconds

**Given** I type a search term in the search box
**When** the query is sent
**Then** results are filtered to items where the term matches title, description, tags, or content
**And** results return within 500ms for a library of up to 1,000 items
**And** if no results match, a "No results found" empty state is shown

**Given** I apply a content_type filter (Skill / Prompt)
**When** the filter is active
**Then** only items of the selected type are shown

**Given** I apply a target_ai filter (e.g. claude, github-copilot)
**When** the filter is active
**Then** only items targeting that AI assistant are shown

**Given** I apply a tags filter
**When** a tag is selected
**Then** only items with that tag are shown

**Given** filters are combined (type + target_ai + search query)
**When** the combined filter is applied
**Then** results satisfy ALL active filters simultaneously (AND logic)

**Given** GET /api/v1/library/items is called with a valid JWT
**Then** the response follows the standard envelope: {items, total, page, size, pages}
**And** query parameters ?type=, ?tags=, ?target_ai=, ?q=, ?page=, ?size= are all supported

**Given** GET /api/v1/library/items is called without a JWT
**Then** the response is HTTP 401

---

### Story 4.3: Library Item Detail View & Copy-to-Clipboard

As an authenticated developer,
I want to open any library item and view its full Markdown content with metadata, copy it to clipboard, and jump to its GitHub source,
So that I can use the skill or prompt immediately in my AI assistant workflow.

**Acceptance Criteria:**

**Given** I click on a library item card from the /library page
**When** the detail view opens (inline drawer, modal, or /library/{slug} route)
**Then** I see the full Markdown content rendered with syntax highlighting
**And** I see the item's metadata: content_type, title, description, tags, target AI assistants, author (GitHub handle), last updated date
**And** the content_type badge (Skill / Prompt) is clearly visible

**Given** I click the "Copy to clipboard" button
**When** the action fires
**Then** the raw Markdown content is copied to the system clipboard
**And** a toast notification confirms "Copied to clipboard"

**Given** I click the "View on GitHub" link
**When** the link is activated
**Then** it opens the source file in the GitHub content repository in a new browser tab
**And** the URL points to the correct path (/skills/{slug}/SKILL.md or /prompts/{slug}.md)

**Given** GET /api/v1/library/items/{slug} is called with a valid JWT
**Then** the response contains all item fields including the full raw content

**Given** GET /api/v1/library/items/{slug} is called for a non-existent slug
**Then** the response is HTTP 404

**Given** GET /api/v1/library/items/{slug} is called without a JWT
**Then** the response is HTTP 401

**Given** an item has is_public=false
**When** GET /api/v1/library/items/public is called
**Then** that item does NOT appear in the response

**Given** the library cache is empty (Redis has no library:items key)
**When** GET /api/v1/library/items is called
**Then** the response returns an empty items list and total: 0 (no 500 error)
