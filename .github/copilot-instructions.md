# GitHub Copilot Instructions — idp-app

## Project Overview

**idp-app** is an **Integrated Developer Portal** — a monorepo containing:

- **Backend:** Python 3.12+ / FastAPI, async PostgreSQL (asyncpg + SQLAlchemy 2), Celery + Redis, JWT auth
- **Frontend:** React 19 + TypeScript, Vite, MUI v6, TanStack Query, React Router v7, Axios
- **Tooling:** [pixi](https://prefix.dev/docs/pixi/) manages all environments and tasks (replaces Make, Poetry, venv, nvm)
- **Containerisation:** Docker Compose (backend, frontend/nginx, postgres, redis)

---

## Repository Structure

```
pixi.toml               # Root workspace — all pixi tasks & env declarations
backend/
  pyproject.toml        # Python project + all tool configs (ruff, mypy, pytest, bandit)
  pixi.toml             # pixi-build manifest (conda packaging only)
  src/idp_app/          # Application package
    main.py             # App factory (create_app)
    api/v1/             # Versioned API routers & route modules
    core/               # config, database, security
    models/             # SQLAlchemy ORM models
    schemas/            # Pydantic request/response schemas
    tasks/              # Celery worker & task definitions
  alembic/              # Database migrations
  tests/                # pytest async test suite
frontend/
  src/
    api/client.ts       # Axios instance (base URL, JWT interceptor, 401 handling)
    components/         # Reusable React components
    pages/              # Page-level components (route targets)
    theme/              # MUI theme configuration
docker/                 # Dockerfiles for backend and frontend/nginx
```

---

## Running Common Tasks

All tasks run via `pixi run <task>`. **Never use bare `npm`, `pytest`, or `ruff` directly.**

| Task | Command |
|---|---|
| One-time setup (after clone) | `pixi run setup` |
| Run all quality checks | `pixi run check` |
| Backend dev server | `pixi run backend-run` |
| Frontend dev server | `pixi run frontend-dev` |
| Run all tests | `pixi run test` |
| Backend tests only | `pixi run backend-test` |
| Frontend tests only | `pixi run frontend-test` |
| Lint all code | `pixi run lint` |
| Format all code | `pixi run format` |
| Apply DB migrations | `pixi run backend-migrate` |
| Generate new migration | `pixi run backend-migration -m "description"` |
| Start all Docker services | `pixi run docker-up` |

---

## Backend Conventions

### Language & Runtime
- Python **3.12+** is required. Use modern syntax: `X | Y` union types, `dict[str, Any]`, `list[str]` (no `Optional`, `Dict`, `List` from `typing`).
- Use `from __future__ import annotations` only when needed for forward references; prefer runtime annotations otherwise.
- All async I/O uses `async`/`await`. Never use synchronous DB or network calls in route handlers.

### Module layout
- `idp_app.core.config` — Settings via `pydantic-settings`. Access via `get_settings()` (LRU-cached singleton). Do **not** instantiate `Settings()` directly.
- `idp_app.core.database` — Async engine + `get_db()` FastAPI dependency. Use `Annotated[AsyncSession, Depends(get_db)]` in route signatures.
- `idp_app.core.security` — `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`.
- `idp_app.models.*` — SQLAlchemy ORM models extending `Base`. Use `Mapped[T]` / `mapped_column()` (SQLAlchemy 2 style). Always add `__repr__`.
- `idp_app.schemas.*` — Pydantic v2 schemas for request/response. Separate `Create`, `Update`, `Read`/`Response` schemas per resource.
- `idp_app.api.v1.routes.*` — One file per resource (e.g. `users.py`, `auth.py`). Each exports a `router = APIRouter()`.
- `idp_app.tasks.worker` — Celery application and task definitions.

### API patterns
- All routes live under `/api/v1/` (prefix set in `Settings.API_V1_PREFIX`).
- Use `Annotated[..., Depends(...)]` for all dependency injection — never positional `Depends()`.
- Return typed `response_model` on every endpoint.
- Use `status.HTTP_*` constants from FastAPI instead of raw integers.
- Raise `HTTPException` with appropriate status codes; include a `detail` string.
- OpenAPI docs (`/docs`, `/redoc`) are only available when `DEBUG=True`.

### Pydantic / settings
- Use `pydantic-settings` `BaseSettings` for all configuration. Settings are loaded from env vars and `.env`.
- `ALLOWED_ORIGINS` is a comma-separated string; use `settings.parse_allowed_origins()` to get the list.
- Use `PostgresDsn` / `RedisDsn` validators for URL settings.

### Database / migrations
- Use `AsyncSession` from SQLAlchemy 2 for all DB operations.
- Always `await session.commit()` via the `get_db()` dependency (it commits on success, rolls back on exception).
- Schema changes require an Alembic autogenerate migration: `pixi run backend-migration -m "message"`.
- Migration files live in `backend/alembic/versions/`. Filename convention: `YYYYMMDD_HHMM_<hash>_<slug>.py`.

### Testing
- Framework: **pytest** with `pytest-asyncio` (`asyncio_mode = "auto"`).
- Test DB: in-memory **SQLite + aiosqlite** (`sqlite+aiosqlite:///:memory:`) via `StaticPool` — no real Postgres needed.
- Fixtures: `test_engine`, `db_session`, `app`, `client` are provided in `tests/conftest.py`.
- HTTP testing: `AsyncClient` with `ASGITransport` — never spin up a real HTTP server in tests.
- Coverage threshold: **80%** (`--cov-fail-under=80`).
- Test files are named `test_<module>.py` and mirror the source structure.

### Code quality
- **Linter/formatter:** `ruff` (config in `backend/pyproject.toml`). Run `pixi run backend-lint-fix` then `pixi run backend-format`.
- **Type-checker:** `mypy` (strict). All public functions must have complete type annotations.
- **Security scanner:** `bandit` (level `ll` — medium+). Run `pixi run backend-security`.
- All three must pass cleanly before merging.

---

## Frontend Conventions

### Language & Runtime
- **TypeScript** (strict mode). No `any` except where unavoidable — use `unknown` instead.
- React **functional components only** — no class components.
- Use named exports for all components.

### State & data fetching
- Remote state: **TanStack Query** (`@tanstack/react-query`). Define query keys as constants.
- Local UI state: React `useState` / `useReducer`.
- All API calls go through `src/api/client.ts` (`apiClient` Axios instance).
  - JWT token is attached automatically via request interceptor.
  - 401 responses automatically clear the token and redirect to `/login`.

### Component conventions
- One component per file; file name matches the component name (`PascalCase.tsx`).
- Co-locate tests: `ComponentName.test.tsx` alongside `ComponentName.tsx`.
- Use **MUI v6** (`@mui/material`) for all UI primitives. Extend the theme in `src/theme/index.ts`.
- Emotion (`@emotion/react`, `@emotion/styled`) for custom styled components.

### Routing
- **React Router v7** (`react-router-dom`). Route definitions live in `App.tsx`.

### Testing
- Framework: **Vitest** + **@testing-library/react** + **@testing-library/user-event**.
- Test setup file: `src/test/setup.ts` (imports `@testing-library/jest-dom`).
- Config: `vitest.config.ts` (jsdom environment).
- Test files: `*.test.tsx` / `*.test.ts` co-located with source.

### Code quality
- **ESLint** (flat config `eslint.config.js`): react, react-hooks, jsx-a11y, security, typescript-eslint plugins. `--max-warnings=0` — zero warnings allowed.
- **Prettier** for formatting. Config in `package.json` or `prettier.config.*`.
- **TypeScript** strict mode — `tsc --noEmit` must pass.
- **audit-ci** for dependency security (`npm run security`).

---

## Security Requirements
- Passwords are hashed with **bcrypt** via `passlib`.
- JWT tokens use **HS256** with the `SECRET_KEY` setting. Access tokens expire in 30 minutes.
- `SECRET_KEY` must be overridden in production. The default value is development-only.
- Never log passwords, tokens, or secrets.
- Never commit `.env` files.

---

## Git & Commit Conventions
- Use **Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, etc.).
- The `commit-msg` pre-commit hook enforces this format.
- Changelog is generated by **git-cliff** (`pixi run changelog`).

---

## Docker
- Multi-service setup: `backend`, `frontend` (nginx), `postgres`, `redis`.
- The backend `Dockerfile` is at `docker/backend/Dockerfile`; frontend at `docker/frontend/Dockerfile`.
- Dev override: `docker-compose.override.yml` (e.g. volume mounts, port exposure).
- Apply migrations inside the running container with `pixi run docker-migrate`.

---

## Key Dependencies Reference

| Layer | Dependency | Purpose |
|---|---|---|
| Backend | `fastapi` | REST API framework |
| Backend | `sqlalchemy 2` + `asyncpg` | Async ORM + PostgreSQL driver |
| Backend | `alembic` | Database migrations |
| Backend | `celery` + `redis-py` | Background task queue |
| Backend | `pydantic-settings` | Settings from env |
| Backend | `python-jose` + `passlib[bcrypt]` | JWT + password hashing |
| Backend | `httpx` | HTTP client (and test transport) |
| Frontend | `react` + `react-router-dom` | SPA framework + routing |
| Frontend | `@mui/material` | Component library |
| Frontend | `@tanstack/react-query` | Server state management |
| Frontend | `axios` | HTTP client |
| Tooling | `pixi` | Monorepo task runner + env manager |
| Tooling | `ruff` | Python linter + formatter |
| Tooling | `mypy` | Python type checker |
| Tooling | `vitest` | Frontend test runner |
| Tooling | `git-cliff` | Changelog generation |
