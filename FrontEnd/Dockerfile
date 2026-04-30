# FrontEnd/Dockerfile
# Multi-stage build:
#   Stage 1 (builder): node:20-alpine — npm ci + vite build → /app/dist
#   Stage 2 (runtime): nginxinc/nginx-unprivileged:1.27-alpine — serve static
#
# Hardening rationale:
#   - nginx-unprivileged: runs as UID 101 (high UID per CKV_K8S_40), listens
#     on port 8080 (unprivileged port), writes pid to /tmp instead of /var/run.
#     This is the canonical non-root nginx image maintained by the nginx team.
#   - K8s Service maps :80 (cluster) -> :8080 (pod), so external API unchanged.
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
FROM nginxinc/nginx-unprivileged:1.27-alpine

# nginx-unprivileged listens on 8080 by default. Our nginx.conf has been
# updated to `listen 8080;` accordingly (see FrontEnd/nginx.conf).
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# Image runs as UID 101 (nginx) by default — no need for explicit USER.
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
