# BackEnd/Dockerfile
# Multi-stage build with uv:
#   Stage 1 (builder): uv sync 安装所有依赖到 /app/.venv
#   Stage 2 (runtime): 只复制 .venv + 应用代码，uv 本身不进最终镜像
#
# 分层说明：
#   builder 层装了 uv、gcc 等构建工具，最终镜像不包含这些，保持镜像小。
#   依赖层（uv sync）和代码层（COPY . .）分开，代码改动不会使依赖缓存失效。
#
# Hardening（与原版一致）：
#   - non-root UID 10001 (CKV_K8S_23/40)
#   - SeccompProfile RuntimeDefault（由 K8s manifest 控制）
#   - HEALTHCHECK 供 docker run / compose 使用

# ── Stage 1: builder ─────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 构建依赖（ortools、cryptography 等需要编译）
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libffi-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖声明，利用 Docker layer cache：
# 只有 pyproject.toml / uv.lock 变了才重新 sync，代码改动不触发重装
COPY pyproject.toml uv.lock ./

# --frozen        : 严格按 uv.lock，不更新
# --no-dev        : 不装开发/测试依赖
# --no-install-project : 只装依赖，不装项目本身（下一层再 COPY 代码）
RUN uv sync --frozen --no-dev --no-install-project

# ── Stage 2: runtime ─────────────────────────────────────────────────────
FROM python:3.12-slim

# Patch base image vulns（Trivy CRITICAL/HIGH gating）
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends openssl libssl3 \
 && rm -rf /var/lib/apt/lists/*

# 非 root 用户（UID 10001）
RUN groupadd --system --gid 10001 appgroup \
 && useradd --system --uid 10001 --gid appgroup \
            --no-create-home --shell /sbin/nologin appuser

WORKDIR /app

# 只复制 builder 里装好的 venv，uv 本身留在 builder 不带入
COPY --from=builder /app/.venv /app/.venv

# 把 venv 的 bin 放进 PATH，之后直接用 python / uvicorn 即可
ENV PATH="/app/.venv/bin:$PATH"

# 复制应用代码（代码层和依赖层分开，改代码不使依赖缓存失效）
COPY --chown=appuser:appgroup . .

USER 10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/docs', timeout=3).status == 200 else 1)" \
  || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]