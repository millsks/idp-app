# Story 4.1: GitHub Content Sync Service

Status: ready-for-dev

## Story

As a portal administrator,
I want library content to be automatically synced from the GitHub content repository and cached in Redis,
so that the library always reflects the latest published skills and prompts without manual intervention.

## Acceptance Criteria

1. A Celery task `library.sync_content` exists and runs on application startup and every `LIBRARY_CACHE_TTL` seconds (default 900) via Celery Beat.
2. The task fetches the repository file tree from the GitHub API using `GITHUB_CONTENT_TOKEN` and identifies all `/skills/{slug}/SKILL.md` and `/prompts/{slug}.md` paths.
3. For each skill, the task fetches `/skills/{slug}/SKILL.md` content and `/skills/{slug}/README.md` (for description fallback), decodes base64 content, and parses YAML frontmatter (`title`, `description`, `tags`, `is_public`, `target_ai`).
4. For each prompt, the task fetches `/prompts/{slug}.md`, decodes content, and parses YAML frontmatter.
5. For each item, the task derives `author` and `last_updated` from the file's most recent commit metadata via the GitHub commits API.
6. All items are written atomically to Redis: each item at `library:item:{slug}` (Hash), slug added to `library:items` (Set), public items (`is_public=true`) added to `library:items:public` (Set).
7. After successful sync, `library:last_refresh` is set to the current Unix timestamp and `library:sync_status` is set to `"ok"`.
8. On GitHub API error: the task retries with exponential backoff, sets `library:sync_status = "error:{message}"`, logs a structured error, and does NOT delete existing cached items (stale cache preserved on error).
9. When the GitHub API rate limit reaches 80% of 5,000 req/hr, the task logs a structured warning with the current rate limit counter.
10. `POST /api/v1/library/refresh` with a valid superuser JWT returns HTTP 202 and enqueues an immediate `library.sync_content` Celery task.
11. `POST /api/v1/library/refresh` with a non-superuser JWT returns HTTP 403.
12. New Settings fields are wired and validated: `GITHUB_CONTENT_TOKEN`, `GITHUB_CONTENT_OWNER`, `GITHUB_CONTENT_REPO`, `GITHUB_CONTENT_BRANCH`, `LIBRARY_CACHE_TTL`.
13. All new env vars are present in `.env.example` with inline documentation comments.

## Tasks / Subtasks

- [ ] Add new Settings fields to `core/config.py` (AC: 12, 13)
  - [ ] `GITHUB_CONTENT_TOKEN`, `GITHUB_CONTENT_OWNER`, `GITHUB_CONTENT_REPO`, `GITHUB_CONTENT_BRANCH` (default: `"main"`), `LIBRARY_CACHE_TTL` (default: `900`)
  - [ ] Update `.env.example`
- [ ] Create `services/github_content.py` — GitHub API client (AC: 2, 3, 4, 5, 9)
  - [ ] `get_file_tree(owner, repo, branch)` — calls GitHub Trees API, returns filtered list of skill/prompt paths
  - [ ] `get_file_content(owner, repo, path)` — calls GitHub Contents API, decodes base64
  - [ ] `get_last_commit(owner, repo, path)` — calls GitHub Commits API, returns `{author, last_updated}`
  - [ ] `parse_frontmatter(content: str)` — extracts YAML frontmatter block from Markdown, returns dict
  - [ ] Rate limit header parsing: read `X-RateLimit-Remaining` and `X-RateLimit-Limit` from response headers; log warning at 80%
  - [ ] All HTTP calls use `httpx.AsyncClient` with the `Authorization: Bearer {GITHUB_CONTENT_TOKEN}` header
- [ ] Create `tasks/library_sync.py` — Celery sync task (AC: 1–9)
  - [ ] `@celery_app.task(name="library.sync_content")` decorated function
  - [ ] Async wrapper pattern for Celery + asyncio (use `asyncio.run()` inside task)
  - [ ] Set `library:sync_status = "running"` at start
  - [ ] Fetch file tree → iterate paths → fetch content + commit data → parse frontmatter
  - [ ] Atomic Redis pipeline: delete old `library:items` Set, write all new items, rebuild Sets
  - [ ] On exception: catch all, log structured error, set `library:sync_status = "error:{msg}"`, re-raise
  - [ ] Retry config: `max_retries=3`, exponential backoff (`countdown=2**retries`)
- [ ] Update `tasks/worker.py` — add Celery Beat schedule (AC: 1)
  - [ ] `celery_app.conf.beat_schedule["sync-library-content"]` using `LIBRARY_CACHE_TTL` from settings
- [ ] Add `POST /api/v1/library/refresh` endpoint to `api/v1/routes/library.py` (AC: 10, 11)
  - [ ] Requires `Annotated[User, Depends(get_current_user)]`
  - [ ] Checks `current_user.is_superuser` — raises HTTP 403 if false
  - [ ] Enqueues `sync_library_content.delay()` — returns HTTP 202
- [ ] Write tests in `tests/test_library_sync.py`
  - [ ] Mock GitHub API responses (tree, content, commits)
  - [ ] Test successful sync writes correct Redis keys
  - [ ] Test error handling preserves stale cache
  - [ ] Test rate limit warning is logged
  - [ ] Test refresh endpoint superuser gate

## Dev Notes

- Use `httpx.AsyncClient` for all GitHub API calls — already available as a dependency. Do NOT use the `requests` library.
- YAML frontmatter parsing: the frontmatter block is the content between `---` delimiters at the top of the file. Use `python-frontmatter` library or parse manually with `yaml.safe_load`. Add `python-frontmatter` to dependencies if using it.
- Atomic Redis pipeline for sync: use `redis.pipeline()` context manager. The pipeline should: `DELETE library:items`, `DELETE library:items:public`, then `SADD library:items slug1 slug2 ...`, `SADD library:items:public public_slug1 ...`, `HSET library:item:{slug} field1 val1 ...` for each item — all in one `pipeline.execute()`.
- Redis Hash field values must be strings. Serialize lists (`tags`, `target_ai`) as JSON strings. Deserialize on read.
- Celery task running asyncio: Celery workers run synchronously by default. Use `asyncio.run(async_sync_function())` inside the Celery task function — do not use `async def` at the task level unless the worker is configured for `gevent`/`eventlet`.
- `LIBRARY_CACHE_TTL` in Beat schedule: access via `get_settings()` inside `beat_schedule` setup. Ensure settings are loaded after app initialisation.
- The `library:items` Redis keys have no TTL — they persist until the next sync overwrites them. This is intentional (stale cache on error).

### Project Structure Notes

- Modify: `backend/src/idp_app/core/config.py` — add content repo + cache Settings fields
- Create: `backend/src/idp_app/services/github_content.py`
- Create: `backend/src/idp_app/tasks/library_sync.py`
- Modify: `backend/src/idp_app/tasks/worker.py` — add Beat schedule
- Modify: `backend/src/idp_app/api/v1/routes/library.py` — add `/refresh` endpoint
- Modify: `.env.example`
- Create: `backend/tests/test_library_sync.py`

### References

- Architecture Section 2.3: GitHub Content Service Architecture [Source: _bmad-output/planning-artifacts/architecture.md#23-github-content-service-architecture]
- Architecture ARCH-4 – ARCH-9 [Source: _bmad-output/planning-artifacts/architecture.md#additional-requirements-from-architecture]
- Architecture Section 7: Security Checklist items 7, 12 [Source: _bmad-output/planning-artifacts/architecture.md#7-security-checklist]
- PRD FR-5.3, FR-5.4, FR-5.5, FR-5.12, FR-5.13, NFR-4.2.2, NFR-4.4.1 [Source: _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
