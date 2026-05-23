# IDP App — Backend

FastAPI + PostgreSQL + Celery backend for the Integrated Developer Portal.

## Quick Start (via pixi from the repo root)

```bash
pixi run backend-run      # start dev server on :8000
pixi run backend-worker   # start Celery worker
pixi run backend-migrate  # run DB migrations
```

## Testing

```bash
pixi run backend-test          # run full test suite
pixi run backend-test-coverage # generate HTML coverage report
```

## Code Quality

```bash
pixi run backend-check   # lint + format-check + typecheck + test + security
pixi run backend-lint
pixi run backend-format
pixi run backend-typecheck
pixi run backend-security
```

## Database Migrations

```bash
# Create a new migration
pixi run backend-migration -- -m "add new table"

# Apply all pending migrations
pixi run backend-migrate

# Roll back the last migration
pixi run backend-migrate-down
```
