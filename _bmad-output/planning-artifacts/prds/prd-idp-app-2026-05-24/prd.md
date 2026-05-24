---
title: "idp-app — MVP1 Product Requirements Document"
status: final
created: 2026-05-24
updated: 2026-05-24
version: 1.0
project: idp-app
milestone: MVP1
---

# idp-app — MVP1 Product Requirements Document

## 1. Overview

### 1.1 Problem Statement

Developers waste significant time hunting across disparate tools, repositories, and documentation to find reusable AI prompts, agentic skills, and prompt templates for their daily work. There is no single curated, versioned, and community-accessible place to discover, contribute to, and build on a shared AI skills and prompts toolkit. Existing solutions (GitHub gists, personal notes, team wikis) are unstructured, non-searchable, and easily become stale.

### 1.2 Product Vision

**idp-app** is an open-source Integrated Developer Portal — a single pane of glass that centralises the tools, knowledge, and utilities that developers need to move faster and work smarter. It will grow across multiple release milestones into a comprehensive developer experience platform.

> **MVP1 focus:** Deliver a public-facing portal with authenticated access, social login, and a live AI Skills & Prompts Library backed by GitHub for versioning and community contribution.

### 1.3 Goals (MVP1)

| Goal | Measure of Success |
|------|--------------------|
| Developers can register and log in using their existing Google or GitHub accounts | OAuth2 social login flow completes end-to-end; user record created on first login |
| Authenticated users can view and manage their profile | Profile page accessible only when logged in; displays identity info from OAuth provider |
| Authenticated users can browse, search, and view AI skills and prompts | Library page loads with at least seed content; search returns relevant results |
| Public visitors can discover the portal's value before signing in | Public landing page clearly communicates the portal's purpose and capability pillars |
| All library content is versioned and recoverable | Every skill/prompt change is tracked in GitHub; content is loaded from a configured GitHub repository |

### 1.4 Non-Goals (MVP1)

The following are explicitly **out of scope** for MVP1 and will be addressed in subsequent milestones:

- Software Marketplace (curated app downloads)
- VSCode extension registry mirror
- Developer Utilities (JWT decoder, Base64, JSON formatter, etc.)
- Application Accelerators / project scaffolding
- NVD Vulnerability Library
- Tech Radar
- Service Catalog
- Team / organisation management
- User-to-user social features (follows, likes, comments)
- Contributing new skills/prompts via the UI (read-only library in MVP1; contributions via GitHub PR)

---

## 2. Target Users (MVP1)

### 2.1 Primary User: Individual Developer (Authenticated)

A software developer who works daily with AI assistants (GitHub Copilot, Claude, ChatGPT, Cursor). They want a curated, searchable library of prompts and agentic skills they can copy, adapt, and reuse — without maintaining their own scattered collection.

**Key behaviours:**
- Logs in via GitHub (they already have an account; lowest friction)
- Searches the library by tool, language, or use-case keyword
- Copies a skill or prompt to clipboard or views raw content
- Does not need to contribute content via the UI in MVP1 — contributions happen through a GitHub PR

### 2.2 Secondary User: Public Visitor (Unauthenticated)

A developer who has landed on the portal (via search, social media, or word of mouth) and has not yet signed up. They need enough information to understand the value proposition and be converted to a registered user.

**Key behaviours:**
- Lands on the public landing page
- Can browse a high-level description of each capability pillar
- Cannot access the library without logging in
- Can see a preview of public skills and prompts on the landing page to demonstrate value before signing up

### 2.3 Portal Administrator

For MVP1, the portal administrator is the repo owner (Millsks). Admin capabilities are limited to what is accessible via the existing `is_superuser` flag in the User model. No dedicated admin UI is required in MVP1.

---

## 3. Functional Requirements

### Feature 1 — Public Landing Page

**FR-1.1** The landing page SHALL be accessible to unauthenticated users without any login prompt.

**FR-1.2** The landing page SHALL communicate the portal's purpose in a headline and supporting copy.

**FR-1.3** The landing page SHALL surface the planned capability pillars (Skills & Prompts Library, Software Marketplace, Developer Utilities, Application Accelerators, Vulnerability Library) as visual cards or sections — even if not all are live in MVP1 — to communicate the product roadmap and value.

**FR-1.4** The landing page SHALL include clear call-to-action to sign in or register.

**FR-1.5** The landing page SHALL include links to the project's GitHub repository (open-source disclosure).

**FR-1.6** A preview strip of recent or featured public skills/prompts SHALL be visible on the landing page to demonstrate library value to unauthenticated visitors. Clicking an item shows title and description only; full content requires authentication.

---

### Feature 2 — Authentication & Social Login

**FR-2.1** The system SHALL support user registration and login via **GitHub OAuth2**.

**FR-2.2** The system SHALL support user registration and login via **Google OAuth2**.

**FR-2.3** OAuth2 flows SHALL be implemented using **Authlib** directly against the provider APIs (no hosted identity service).

**FR-2.4** On first successful OAuth2 login, the system SHALL create a new user record in the database, populated with the profile data returned by the provider (display name, email, provider-issued avatar URL).

**FR-2.5** On subsequent logins, the system SHALL update the user record with any changed profile fields from the provider.

**FR-2.6** A user authenticated via social login SHALL receive a short-lived JWT access token (HS256, 30-minute expiry) consistent with the existing token scheme.

**FR-2.7** JWT access tokens SHALL be stored **in-memory only** on the frontend (React context). Tokens SHALL NOT be written to `localStorage` or `sessionStorage`.

**FR-2.7a** On page refresh, the user SHALL be required to re-authenticate. A silent re-auth flow via HttpOnly refresh cookie is out of scope for MVP1 and is the designated MVP2 enhancement for session continuity.

**FR-2.8** The login page SHALL present both social login buttons ("Continue with GitHub", "Continue with Google") prominently. A username/password form SHALL **not** be exposed in the MVP1 UI.

**FR-2.9** The system SHALL handle OAuth2 provider errors gracefully — invalid state, denied callback, revoked token — and return the user to the login page with a clear error message.

**FR-2.10** Logging out SHALL invalidate the frontend token and redirect the user to the public landing page.

---

### Feature 3 — User Profile

**FR-3.1** An authenticated user SHALL be able to access a `/profile` page that is protected from unauthenticated access.

**FR-3.2** The profile page SHALL display: display name, email address, provider avatar image, account creation date, and OAuth2 provider identity (GitHub / Google).

**FR-3.3** The user SHALL be able to update their **display name** on the profile page.

**FR-3.4** Email address SHALL be read-only on the profile page (sourced from OAuth provider). Users cannot change their portal email in MVP1.

**FR-3.5** The backend SHALL expose a `GET /api/v1/users/me` endpoint that returns the authenticated user's record. This endpoint SHALL require a valid JWT Bearer token.

**FR-3.6** The backend SHALL expose a `PATCH /api/v1/users/me` endpoint that allows updating the display name. This endpoint SHALL require a valid JWT Bearer token.

---

### Feature 4 — Authenticated Route Protection

**FR-4.1** All non-public routes SHALL redirect unauthenticated users to the login page.

**FR-4.2** After successful login, the user SHALL be redirected to the page they originally attempted to access (redirect-on-login pattern) or to the home dashboard if no prior destination exists.

**FR-4.3** The frontend router SHALL implement route-level authentication guards.

**FR-4.4** The API SHALL return `HTTP 401 Unauthorized` for any protected endpoint accessed without a valid token. The frontend JWT interceptor (already wired in `client.ts`) SHALL handle this by clearing the token and redirecting to `/login`.

---

### Feature 5 — AI Skills & Prompts Library

**FR-5.1** The library SHALL be accessible only to authenticated users.

**FR-5.2** The library SHALL contain two distinct content types — **Skills** and **Prompts** — unified under a single `content_type` tag for filtering and API access.

- **Skill:** A reusable agentic instruction set — a SKILL.md file designed to give an AI assistant a persona, workflow, or specialised capability. Each skill has an accompanying README.md providing human-readable context.
- **Prompt:** A single-use or templated instruction string designed to be pasted into an AI chat interface, possibly with variable placeholders.

**FR-5.3** All library content SHALL be stored in and retrieved from a **dedicated GitHub content repository** (separate from the idp-app application repository). The target repository owner, name, and branch SHALL be configurable via environment variables.

**FR-5.4** Library content SHALL be loaded from GitHub at application startup and cached in Redis with a configurable TTL (default: 15 minutes). A cache invalidation endpoint accessible to superusers SHALL allow a forced refresh without restarting the application.

**FR-5.5** Each library item SHALL include: `content_type` (skill | prompt), title, description, category/tags, content (raw Markdown), `is_public` flag, author (GitHub handle from commit metadata), last updated date (from Git commit), and target AI assistant(s) (e.g. GitHub Copilot, Claude, ChatGPT, Cursor — multi-select).

**FR-5.12** Skills SHALL be sourced from `/skills/{slug}/SKILL.md` in the content repository. The accompanying `/skills/{slug}/README.md` SHALL populate the item's description field when present.

**FR-5.13** Prompts SHALL be sourced from `/prompts/{slug}.md` in the content repository.

**FR-5.6** The library page SHALL display skills and prompts in a searchable, filterable list/grid.

**FR-5.7** Search SHALL operate across title, description, tags, and content (full-text).

**FR-5.8** Filters SHALL include: content type (Skill / Prompt), category/tags, and target AI assistant.

**FR-5.9** Each item SHALL have a detail view that displays the full content with syntax highlighting (Markdown rendered), metadata, and a "Copy to clipboard" action.

**FR-5.10** A "View on GitHub" link SHALL be present on each item detail view, pointing to the source file in the content repository and enabling contributors to open a PR for corrections.

**FR-5.11** The library SHALL include seed content on first launch sourced from the dedicated GitHub content repository. The application owner (Millsks) is responsible for populating the content repository before or at launch. The BMad agent skills in `.agents/skills/` in this repository may optionally be migrated to the content repository as initial seed content.

---

## 4. Non-Functional Requirements

### 4.1 Security

**NFR-4.1.1** OAuth2 state parameter SHALL be validated on callback to prevent CSRF.

**NFR-4.1.2** JWT tokens SHALL use HS256 and expire in 30 minutes consistent with existing `create_access_token` implementation.

**NFR-4.1.3** `SECRET_KEY`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GITHUB_CONTENT_TOKEN` SHALL be supplied via environment variables and NEVER committed to the repository.

**NFR-4.1.4** Genuine passwords SHALL NOT be stored for social-login-only users. The `hashed_password` column SHALL store a cryptographically random, unusable hash for OAuth-only accounts (column remains NOT NULL; the stored value cannot be used to authenticate).

**NFR-4.1.5** All API responses SHALL include appropriate CORS headers; `ALLOWED_ORIGINS` shall be restricted to the deployed frontend origin in production.

**NFR-4.1.6** GitHub API calls for content retrieval SHALL use a scoped Personal Access Token with `contents: read` permission only.

### 4.2 Performance

**NFR-4.2.1** Library list page SHALL load (first contentful paint) in under 2 seconds on a standard broadband connection.

**NFR-4.2.2** GitHub content cache SHALL ensure no user-facing request waits on a live GitHub API call during a cache-hit scenario.

**NFR-4.2.3** Search results SHALL return within 500ms for a library of up to 1,000 items.

### 4.3 Accessibility

**NFR-4.3.1** All pages SHALL meet WCAG 2.1 AA contrast requirements.

**NFR-4.3.2** All interactive elements SHALL be keyboard-navigable.

### 4.4 Observability

**NFR-4.4.1** Application logs SHALL include structured log entries for: login events (provider, success/failure), library cache refresh events, and API errors.

**NFR-4.4.2** The existing `/api/v1/health` endpoint SHALL remain functional and reflect database connectivity status.

### 4.5 Compatibility

**NFR-4.5.1** The frontend SHALL support the latest two stable versions of Chrome, Firefox, Safari, and Edge.

**NFR-4.5.2** The application SHALL be deployable via the existing Docker Compose configuration.

---

## 5. User Journeys

### UJ-1: First-Time GitHub Login

> A developer visits the portal for the first time, clicks "Continue with GitHub", authorises the app, and lands on the Skills library.

1. User arrives at public landing page (`/`)
2. User clicks "Sign In" or the CTA button
3. User is taken to `/login` — sees "Continue with GitHub" and "Continue with Google" buttons
4. User clicks "Continue with GitHub"
5. User is redirected to GitHub's OAuth authorisation page
6. User authorises the idp-app OAuth application
7. GitHub redirects to `/auth/github/callback?code=...&state=...`
8. Backend validates state, exchanges code for access token, retrieves GitHub profile
9. Backend creates user record (first visit) or updates existing record
10. Backend issues idp-app JWT; frontend stores token and redirects to `/library`
11. User sees the Skills & Prompts library with search and filters

### UJ-2: Return Login and Profile Update

1. User visits `/` while unauthenticated
2. User navigates to `/profile` directly — is redirected to `/login`
3. User authenticates via Google
4. Redirect-on-login sends user to `/profile`
5. User sees their display name, avatar, email, and provider badge
6. User edits display name and saves — profile updates immediately

### UJ-3: Browsing and Copying a Skill

1. Authenticated user navigates to `/library`
2. User types "code review" in the search box
3. Results filter to matching skills and prompts
4. User clicks on "bmad-code-review" skill card
5. Detail view shows rendered Markdown content, tags, author, last updated date
6. User clicks "Copy to clipboard" — content is copied; toast confirmation shown
7. User clicks "View on GitHub" — GitHub file opens in new tab

### UJ-4: Public Visitor Conversion

1. Unauthenticated visitor lands on `/`
2. They see headline, capability pillars, and a preview strip of featured skills
3. They click a featured skill card — are shown a teaser (title + description only, content blurred or truncated)
4. A "Sign in to view full content" prompt appears
5. Visitor clicks "Continue with GitHub" — completes UJ-1 from step 4

---

## 6. Data Model Notes

The following changes to the existing data model are required for MVP1. [Full schema to be defined in the Architecture document.]

- **`users` table:** Add `oauth_provider` (varchar), `oauth_provider_id` (varchar), `avatar_url` (varchar). The `hashed_password` column remains NOT NULL; OAuth-only accounts store a cryptographically random unusable hash.
- **`oauth_states`:** CSRF state tokens stored in **Redis** with a 5-minute TTL (not a DB table — Redis provides natural expiry without migration overhead).
- **Library items are NOT stored in the application database.** Content is fetched from the dedicated GitHub content repository and cached in Redis. GitHub is the source of truth. The DB schema does not include a `library_items` table.

---

## 7. Open Questions

All open questions resolved. See `.decision-log.md` entries 11–16 for full rationale.

| # | Question | Resolution |
|---|----------|------------|
| OQ-1 | JWT frontend storage strategy | **In-memory only** (React context). No localStorage/sessionStorage. |
| OQ-2 | Library seed content source | **New dedicated GitHub content repo** (to be created by Millsks) |
| OQ-3 | Unauthenticated content preview | **Mixed public/private** — landing page preview strip is permitted; full content requires login |
| OQ-4 | `hashed_password` for OAuth-only users | **Random unusable hash** stored (NOT NULL); avoids schema constraint issues |
| OQ-5 | GitHub content repo structure | Skills: `/skills/{slug}/SKILL.md` + `/skills/{slug}/README.md`; Prompts: `/prompts/{slug}.md` |
| OQ-6 | Skills vs. Prompts content model | **Separate types, unified by `content_type` tag** for filtering and API access |

---

## 8. Out of Scope Pillars (Captured for Roadmap Visibility)

These pillars will be addressed in MVP2 and beyond. Requirements will be elaborated in future PRD iterations.

| Pillar | Target Milestone | Notes |
|--------|-----------------|-------|
| Software Marketplace (curated downloads: VSCode, PyCharm, etc.) | MVP2 | Curated metadata + download links; no binary hosting |
| VSCode Extension Registry Mirror | MVP2 | vsce-compatible REST API; mirroring job from official marketplace |
| Developer Utilities (JWT decoder, Base64, JSON formatter, YAML validator, Regex playground, Cron builder) | MVP2 | Client-side tools; no backend dependency |
| Application Accelerators (GitHub template repos + in-browser scaffold + downloadable zips) | MVP2 | Mixed approach confirmed |
| NVD Vulnerability Library + Dependency Health Checker | MVP2 | NVD API integration + search indexing |
| Tech Radar | MVP3 | Community curation; requires team/org model |
| Service Catalog | MVP3 | Classic IDP pillar; requires org/team model |
| ADR Tracker | MVP3 | Pairs with accelerators |
| Team / Organisation Management | MVP3 | Multi-user governance |

---

## 9. Success Metrics (MVP1)

| Metric | Target |
|--------|--------|
| OAuth login success rate | ≥ 95% of initiated flows complete successfully |
| Library page load time (p95) | < 2 seconds |
| Search response time (p95) | < 500ms |
| Lighthouse accessibility score | ≥ 90 |
| Test coverage (backend) | ≥ 80% (existing threshold maintained) |
| Zero known high/critical security vulnerabilities at launch | Bandit + audit-ci clean |

**Counter-metric:** OAuth failure rate — if > 5% of login attempts fail, investigate provider config or callback handling before continuing.

---

## 10. Confirmed Decisions Summary

| Tag | Decision |
|-----|----------|
| A | Skills = SKILL.md-style agentic instruction sets; Prompts = single-use/templated strings. Separate types, unified by `content_type` tag. |
| B | JWT access token stored **in-memory only** (React context). No browser storage. |
| C | Library content fetched from GitHub and cached in Redis. Not stored in the application DB. |
| D | Dedicated GitHub content repository to be created by Millsks. |
| E | No admin UI for MVP1. Admin operations via GitHub or `is_superuser` flag. |
| F | OAuth CSRF state tokens stored in Redis with 5-minute TTL. |
| G | `hashed_password` stores a **random unusable hash** for OAuth-only users (NOT NULL). |
| H | Username/password login NOT exposed in MVP1 UI. Backend remains but only social login surfaces in the frontend. |
