# syntax=docker/dockerfile:1
# docker/backend/Dockerfile — Multi-stage build for the FastAPI backend.
#
# Build backend: pixi-build-python (no hatch / no PyPI packaging).
# Stage 1 (pixi-installer): uses the official pixi image to resolve and
#   install all conda + PyPI runtime deps into a pixi environment.
# Stage 2 (runtime): copies the resolved Python site-packages and the
#   application source into a lean Debian-slim image.

# ---------------------------------------------------------------------------
# Stage 1: pixi-installer — resolve & install all dependencies via pixi
# ---------------------------------------------------------------------------
FROM ghcr.io/prefix-dev/pixi:0.69.0 AS pixi-installer

WORKDIR /app

# Copy pixi manifests first for better layer caching
COPY pixi.toml pixi.lock ./

# LICENSE is referenced as "../LICENSE" in backend/pyproject.toml (relative to
# the backend/ dir), so it must be present at /app/LICENSE inside the builder.
COPY LICENSE ./

# Copy backend package so pixi can perform the editable install
COPY backend/pyproject.toml backend/
COPY backend/src             backend/src

# Install the default environment (backend + backend-dev tools are included,
# but only runtime deps are needed at this stage — dev tools don't hurt since
# they are excluded from the COPY below via the site-packages approach).
RUN pixi install --frozen --no-progress -e default

# ---------------------------------------------------------------------------
# Stage 2: runtime — lean production image
# ---------------------------------------------------------------------------
FROM debian:12-slim AS runtime

WORKDIR /app

# Runtime system libraries required by psycopg2 and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libssl3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire resolved conda environment from the pixi stage.
# This gives us Python, all installed packages, and the uvicorn binary.
COPY --from=pixi-installer /app/.pixi/envs/default /opt/idp-env

# Copy application source (not installed as a package — imported via PYTHONPATH)
COPY backend/src /app/src

# Environment
ENV PATH="/opt/idp-env/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Non-root user
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --no-create-home appuser
USER appuser

EXPOSE 8000

# Uvicorn binary is on PATH from /opt/idp-env/bin
CMD ["uvicorn", "idp_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
