# Deferred Work

## Deferred from: code review of 0-1-upgrade-nodejs-24 (2026-05-24)

- **Mutable `node:24-alpine` Docker tag — no image digest pin** [`docker/frontend/Dockerfile:7`]: The builder stage uses a floating tag. Consider pinning to a digest (e.g., `node:24-alpine@sha256:...`) for reproducible builds. Pre-existing pattern — `node:22-alpine` was also unpinned.
- **`>=24,<25` upper bound requires manual bump when Node.js 26 LTS arrives** [`pixi.toml:18`]: When Node.js 26 enters Active LTS (expected ~Oct 2028), the constraint will need updating to `>=26,<27` (or `>=24,<27` for a wider window). Intentional by design, consistent with `python = ">=3.12,<3.14"` convention.
