# BackEnd/Dockerfile
# Multi-stage build:
#   Stage 1 (builder): compile native deps + build wheels
#   Stage 2 (runtime): copy installed deps + app code, run as non-root
#
# Hardening rationale (per checkov scan):
#   - non-root user (CKV_K8S_23/40):  run as UID 10001 (high UID, no host conflict)
#   - read-only friendly:              app dir owned by appuser; /tmp emptyDir from K8s
#   - dependency layering:              install layer separate from app code layer for cache
# ──────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ────────────────────────────────────────────────────────
FROM python:3.12-slim

# Patch base image vulns (Trivy CRITICAL/HIGH gating)
RUN apt-get update && apt-get upgrade -y --no-install-recommends openssl libssl3 && rm -rf /var/lib/apt/lists/*

# Create a dedicated non-root user (UID 10001 — high UID per CKV_K8S_40)
# Using --system avoids creating a home dir / mailbox.
RUN groupadd --system --gid 10001 appgroup && \
    useradd  --system --uid 10001 --gid appgroup --no-create-home --shell /sbin/nologin appuser

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy application code with appuser ownership (so readOnlyRootFilesystem
# in K8s doesn't break read access)
COPY --chown=appuser:appgroup . .

# Drop privileges
USER 10001

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
