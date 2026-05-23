# syntax=docker/dockerfile:1
# docker/frontend/Dockerfile — Multi-stage build for the React frontend.

# ---------------------------------------------------------------------------
# Stage 1: builder — install deps and build the Vite bundle
# ---------------------------------------------------------------------------
FROM node:22-alpine AS builder

WORKDIR /build

# Copy package manifests first for layer caching
COPY frontend/package.json frontend/package-lock.json* ./

# Install all dependencies (including devDependencies needed for build)
RUN npm ci --prefer-offline

# Copy the full frontend source
COPY frontend/ ./

# Build the production bundle
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: runtime — serve the built assets via Nginx
# ---------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# Remove the default Nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy Vite build output
COPY --from=builder /build/dist /usr/share/nginx/html

# Nginx config that:
#   - Serves the SPA (catch-all → index.html for client-side routing)
#   - Proxies /api/* to the backend container
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
