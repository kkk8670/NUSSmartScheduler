# FrontEnd/Dockerfile
# Multi-stage build:
#   Stage 1 (builder): node:20-alpine — npm ci + vite build → /app/dist
#   Stage 2 (runtime): nginxinc/nginx-unprivileged:1.29-alpine
#
# Why nginxinc/nginx-unprivileged?
#   - Runs as UID 101 by default (matches K8s deployment securityContext)
#   - Listens on port 8080 (unprivileged port; matches Service targetPort)
#   - Writes pid/cache to /tmp (allows readOnlyRootFilesystem in K8s)
#
# Why version 1.29-alpine?
#   - Tracks the current stable nginx mainline + latest alpine 3.22
#   - Trivy CRITICAL/HIGH gate (CI) requires up-to-date base image packages
# ──────────────────────────────────────────────────────────────────────────

FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_BACKEND_URL=http://localhost:8000
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}
RUN npm run build

# ── Runtime stage ────────────────────────────────────────────────────────
FROM nginxinc/nginx-unprivileged:1.29-alpine

# Apply latest alpine security patches on top of the base (Trivy gate).
# `apk upgrade` here ensures we ship the most up-to-date system packages
# even when the upstream image hasn't been rebuilt recently.
USER 0
RUN apk update && apk upgrade --no-cache && rm -rf /var/cache/apk/*
USER 101

# nginx-unprivileged listens on 8080 by default. Our nginx.conf has been
# updated to `listen 8080;` accordingly (see FrontEnd/nginx.conf).
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
