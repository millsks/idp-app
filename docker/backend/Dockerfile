# syntax=docker/dockerfile:1
# docker/backend/Dockerfile — Multi-stage build for the FastAPI backend.

# ---------------------------------------------------------------------------
# Stage 1: builder — install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build-time system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency metadata first (layer-cache friendly)
COPY backend/pyproject.toml ./

# Install production dependencies into a prefix for easy copying
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install ".[standard]" 2>/dev/null || \
    pip install --no-cache-dir --prefix=/install .

# ---------------------------------------------------------------------------
# Stage 2: runtime — lean image with only what's needed at run time
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed site-packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY backend/src /app/src

# Environment hygiene
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Create a non-root user for running the application
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "idp_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
