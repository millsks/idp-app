# IDP App — Integrated Developer Portal

A full-stack developer portal built with **FastAPI** (backend) and **React + Material UI** (frontend), managed as a monorepo with **Pixi**.

---

## Technology Stack

| Layer       | Technology                                          |
|-------------|-----------------------------------------------------|
| Backend     | Python 3.12+, FastAPI, SQLAlchemy 2, Alembic        |
| Database    | PostgreSQL 17                                       |
| Task Queue  | Celery 5 with Redis broker & result backend         |
| Frontend    | React 19, TypeScript, Vite, Material UI v6          |
| Environment | Pixi (conda-forge + PyPI)                           |
| Containers  | Docker Compose                                      |
| CI/CD       | GitHub Actions + nectos/act (local)                 |
| Releases    | Conventional Commits + git-cliff changelogs         |

---

## Prerequisites

- [Pixi](https://pixi.sh/latest/) — `curl -fsSL https://pixi.sh/install.sh | bash`
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for containerised runs)
- [act](https://nektosact.com/installation/) (optional, for local CI runs)

---

## Quick Start

```bash
# 1. Install pixi dependencies + git hooks + frontend npm packages
pixi run setup

# 2. Start all services via Docker Compose
pixi run docker-up

# 3. Run database migrations
pixi run docker-migrate

# 4. Open the portal
#    Backend API:   http://localhost:8000/docs   (DEBUG mode)
#    Frontend:      http://localhost:3000
```

### Local Development (without Docker)

```bash
# Terminal 1 — Backend API (hot-reload)
pixi run backend-run

# Terminal 2 — Celery worker
pixi run backend-worker

# Terminal 3 — Frontend dev server (proxies /api → :8000)
pixi run frontend-dev
```

---

## Project Structure

```text
idp-app/
├── backend/                    # Python / FastAPI application
│   ├── src/idp_app/            #   Application source package
│   │   ├── api/v1/             #   REST API routes
│   │   ├── core/               #   Config, DB, security utilities
│   │   ├── models/             #   SQLAlchemy ORM models
│   │   ├── schemas/            #   Pydantic request/response schemas
│   │   └── tasks/              #   Celery background tasks
│   ├── tests/                  #   Pytest test suite
│   ├── alembic/                #   Database migration scripts
│   └── pyproject.toml          #   Python project config (self-contained)
│
├── frontend/                   # React / TypeScript SPA
│   ├── src/
│   │   ├── api/                #   Axios API client
│   │   ├── components/         #   Reusable UI components
│   │   ├── pages/              #   Route-level page components
│   │   ├── theme/              #   Material UI theme
│   │   └── test/               #   Vitest test helpers
│   ├── eslint.config.js        #   ESLint 9 flat config
│   ├── .prettierrc             #   Prettier config
│   ├── vite.config.ts          #   Vite build config
│   ├── vitest.config.ts        #   Vitest test config
│   └── package.json            #   npm scripts & dependencies
│
├── docker/                     # Dockerfiles & Nginx config
├── .github/workflows/          # GitHub Actions CI/CD
├── pixi.toml                   # Monorepo tasks & environments
└── cliff.toml                  # git-cliff changelog config
```

---

## Pixi Tasks

All project commands are exposed as pixi tasks. Run `pixi task list` to see all.

### Backend

| Task                    | Description                                  |
|-------------------------|----------------------------------------------|
| `backend-run`           | Start FastAPI dev server (hot-reload)        |
| `backend-worker`        | Start Celery worker                          |
| `backend-beat`          | Start Celery beat scheduler                  |
| `backend-lint`          | Lint with ruff                               |
| `backend-format`        | Format with ruff                             |
| `backend-typecheck`     | Type-check with mypy                         |
| `backend-security`      | Security scan with bandit                    |
| `backend-test`          | Run pytest suite                             |
| `backend-check`         | Run all backend checks                       |
| `backend-migrate`       | Apply Alembic migrations                     |
| `backend-migration`     | Generate a new migration                     |

### Frontend

| Task                    | Description                                  |
|-------------------------|----------------------------------------------|
| `frontend-dev`          | Start Vite dev server                        |
| `frontend-build`        | Build for production                         |
| `frontend-lint`         | Lint with ESLint                             |
| `frontend-format`       | Format with Prettier                         |
| `frontend-typecheck`    | Type-check with tsc                          |
| `frontend-test`         | Run Vitest suite                             |
| `frontend-security`     | Audit npm dependencies                       |
| `frontend-check`        | Run all frontend checks                      |

### Monorepo / Docker

| Task                    | Description                                  |
|-------------------------|----------------------------------------------|
| `check`                 | Run all quality checks (backend + frontend)  |
| `docker-up`             | Start all Docker services                    |
| `docker-down`           | Stop all Docker services                     |
| `docker-migrate`        | Run migrations inside Docker                 |
| `changelog`             | Regenerate CHANGELOG.md                      |
| `setup`                 | One-time setup (hooks + frontend deps)       |

---

## Code Quality

```bash
pixi run check          # run everything at once
pixi run hooks-run      # run pre-commit hooks manually
pixi run hooks-update   # update hook versions
```

### Backend Tools

- **ruff** — linting + formatting (replaces flake8, black, isort)
- **mypy** — strict static type checking
- **bandit** — security vulnerability scanner
- **pytest** — test runner with coverage ≥ 80%

### Frontend Tools

- **ESLint 9** — linting (TypeScript, React, accessibility, security rules)
- **Prettier** — opinionated code formatting
- **TypeScript** (strict mode) — static type checking
- **Vitest** — fast unit & component tests with coverage ≥ 80%
- **audit-ci** — npm dependency security auditing

---

## Running Workflows Locally (act)

```bash
# Install act (macOS)
brew install act

# Copy secrets template
cp .secrets.example .secrets
# Edit .secrets with real values

# Run the full CI workflow
act

# Run a specific workflow
act -W .github/workflows/ci.yml

# Run a specific job
act -j backend-quality

# Dry run (show what would execute)
act -n
```

---

## Conventional Commits

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat(backend): add user authentication endpoint
fix(frontend): correct layout shift on mobile
docs: update setup instructions
chore(deps): update pixi lockfile
```

The commit-msg pre-commit hook enforces the format automatically.

---

## Contributing

1. Clone the repository
2. Run `pixi run setup` (installs hooks and frontend deps)
3. Create a feature branch: `git checkout -b feat/my-feature`
4. Make changes and run `pixi run check`
5. Commit using conventional commit format
6. Open a pull request against `develop`
