# Story 0.1: Upgrade Node.js to 24

Status: done

## Story

As a developer,
I want all Node.js version pins in the project upgraded from 22 to 24,
so that the project is ready to adopt Node.js 24 LTS once it reaches Active LTS status in October 2026, and benefits from its performance improvements and new language features in the meantime.

## Context

Node.js 24 is slated to become Active LTS in October 2026. The project currently pins `nodejs = ">=22,<24"` in `pixi.toml`, `node:22-alpine` in the frontend Docker image, and `@types/node: "^22.13.0"` in `frontend/package.json`. Node.js is **not** referenced explicitly in any GitHub Actions workflow YAML — it is installed via pixi, so updating the pixi constraint is the primary lever. The frontend Dockerfile builds from a pinned `node:22-alpine` image and must be updated separately.

> **Note:** Node.js 24 is Current (not yet Active LTS) as of May 2026. Teams targeting stability may prefer to wait until October 2026. This story upgrades proactively.

## Acceptance Criteria

1. `pixi.toml` pins `nodejs = ">=24,<25"` so pixi resolves Node.js 24.x in all environments and CI runs.
2. `docker/frontend/Dockerfile` uses `node:24-alpine` as the builder base image.
3. `frontend/package.json` declares `"@types/node": "^24.0.0"` as a devDependency.
4. `frontend/package.json` `engines` field (if present) is updated to `"node": ">=24"`.
5. CI passes — all backend quality, backend test, frontend quality, frontend test, and docker build jobs succeed on the updated versions.
6. No remaining references to `node:22`, `node-version: 22`, or `nodejs.*<24` exist anywhere in tracked files.

## Tasks / Subtasks

- [x] Task 1 — Update pixi.toml Node.js constraint (AC: #1)
  - [x] Change `nodejs = ">=22,<24"` to `nodejs = ">=24,<25"` in root `pixi.toml` (upper bound tightened to `<25` to avoid resolving Node.js 25.x)
  - [x] Run `pixi install` locally and verify the lock file resolves to Node.js 24.x → resolved **v24.16.0**
  - [x] Commit updated `pixi.toml` and `pixi.lock`

- [x] Task 2 — Update frontend Dockerfile (AC: #2)
  - [x] Change `FROM node:22-alpine AS builder` to `FROM node:24-alpine AS builder` in `docker/frontend/Dockerfile`

- [x] Task 3 — Update @types/node devDependency (AC: #3, #4)
  - [x] In `frontend/package.json`, update `"@types/node"` from `"^22.13.0"` to `"^24.0.0"`
  - [x] No `engines` field present in package.json — skipped
  - [x] Ran `npm install` to regenerate `package-lock.json` (50 added, 1 removed, 2 changed); `frontend-typecheck` passes

- [x] Task 4 — Verify no stale references (AC: #6)
  - [x] Grep returned zero results — no stale `node:22` / `nodejs.*<24` references remain

- [x] Task 5 — Run full CI check locally (AC: #5)
  - [x] `pixi run check` passed — backend lint ✅ format ✅ typecheck ✅ tests 22/22 ✅ (80.70% coverage) security ✅ | frontend lint ✅ format ✅ typecheck ✅ tests 5/5 ✅ security audit 0 vulns ✅

## Dev Notes

### Files to Modify

| File | Change |
|---|---|
| `pixi.toml` (root) | `nodejs = ">=22,<24"` → `">=24,<25"` |
| `docker/frontend/Dockerfile` | `FROM node:22-alpine` → `FROM node:24-alpine` |
| `frontend/package.json` | `@types/node: "^22.13.0"` → `"^24.0.0"` |
| `pixi.lock` | Regenerate after pixi.toml change |
| `frontend/package-lock.json` | Regenerate after package.json change |

### Node.js 24 Key Facts (as of May 2026)

- **V8 engine:** V8 13.6 — includes the latest ECMAScript 2025 features
- **npm:** 11.x shipped by default
- **Breaking changes from 22→24:** Mostly internal; no breaking changes known to affect Vite, React, or FastAPI toolchains. TypeScript and ESLint tooling is unaffected.
- **`node:24-alpine`** is available on Docker Hub.
- **`@types/node` v24** is published on npm and aligns with the Node.js 24 global types.

### How Node.js Reaches CI

The GitHub Actions workflows (`ci.yml`, `release.yml`, `maintenance.yml`) do **not** call `actions/setup-node` directly. Node.js is installed via the `prefix-dev/setup-pixi` action, which reads `pixi.toml` from the repo root and resolves the `nodejs` conda package. Updating `pixi.toml` is therefore sufficient to change the Node.js version in all CI jobs.

### pixi.toml Constraint Rationale

Using `">=24,<25"` (rather than `"==24.*"`) follows the existing convention in the project and allows patch-level updates within the Node.js 24 line without requiring a manual bump on every patch release.

### Testing Standards

- All existing frontend tests (`pixi run frontend-test`) must pass unchanged — no test logic needs updating for this version bump.
- The `pixi run check` task runs the full quality suite (lint, format-check, typecheck, security, and tests) and must pass cleanly.
- No new tests are required; this is a version-pin maintenance story.

### Potential Issues

- If any transitive npm dependency declares `engines: { node: "<24" }`, `npm install` will warn. Use `--engine-strict=false` (default behavior) or update the offending dependency.
- `@types/node@24` may introduce new type signatures for built-in modules. Run `pixi run frontend-typecheck` and resolve any newly surfaced errors before marking done.

### Project Structure Notes

- Root `pixi.toml` governs all environment definitions and is the single source of truth for the conda Node.js package used by both local dev and CI.
- `docker/frontend/Dockerfile` uses a separate `node:X-alpine` base image independent of pixi — it must be updated manually.
- There is no `.nvmrc` file in this repo; no change required there.

### References

- [Source: pixi.toml#L18] — current `nodejs = ">=22,<24"` constraint
- [Source: docker/frontend/Dockerfile#L7] — current `FROM node:22-alpine AS builder`
- [Source: frontend/package.json#L36] — current `"@types/node": "^22.13.0"`
- [Source: .github/workflows/ci.yml] — uses `prefix-dev/setup-pixi@v0.9.5`, no direct `node-version` pin
- Node.js release schedule: https://nodejs.org/en/about/previous-releases

## Review Findings

### Tasks (from code review — 2026-05-24)

- [x] [Review][Patch] AC#1 body references `>=24,<26` — should be `>=24,<25` to match implementation [`_bmad-output/implementation-artifacts/0-1-upgrade-nodejs-24.md`]
- [x] [Review][Defer] Mutable `node:24-alpine` Docker tag — no image digest pin [`docker/frontend/Dockerfile:7`] — deferred, pre-existing (original used `node:22-alpine` without digest)
- [x] [Review][Defer] `>=24,<25` upper bound requires manual bump when Node.js 26 LTS arrives [`pixi.toml:18`] — deferred, intentional design consistent with repo convention

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (GitHub Copilot)

### Debug Log References

- Constraint `>=24,<26` resolved to Node.js v25.9.0 (unexpected); corrected to `>=24,<25` to stay on 24.x line.
- `npm ci` failed until `npm install` regenerated `package-lock.json` with `@types/node@24`.

### Completion Notes List

- Updated `pixi.toml` `nodejs` constraint from `>=22,<24` to `>=24,<25`; pixi resolved v24.16.0.
- Updated `docker/frontend/Dockerfile` builder stage from `node:22-alpine` to `node:24-alpine`.
- Updated `frontend/package.json` `@types/node` from `^22.13.0` to `^24.0.0`; regenerated `package-lock.json`.
- Full `pixi run check` suite passed: 22 backend tests, 5 frontend tests, 0 lint/type errors, 0 security findings.

### File List

- `pixi.toml`
- `pixi.lock`
- `docker/frontend/Dockerfile`
- `frontend/package.json`
- `frontend/package-lock.json`
- `_bmad-output/implementation-artifacts/0-1-upgrade-nodejs-24.md`
