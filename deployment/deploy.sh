#!/usr/bin/env bash
# deploy.sh – Build & deploy Smart Scheduler
# Reads ENV_MODE from .env to decide deployment target
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# ── Check .env ───────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: .env not found. Run: cp .env.example .env"
  exit 1
fi

set -a; source "$ENV_FILE"; set +a

ENV_MODE="${ENV_MODE:-k8s-local}"
echo ">>> ENV_MODE = $ENV_MODE"

# ── Build images ─────────────────────────────────────────
echo ">>> Building backend image..."
docker build -t smart_scheduler_backend:latest "$PROJECT_ROOT/BackEnd"

echo ">>> Building frontend image..."
docker build -t smart_scheduler_frontend:latest \
  --build-arg VITE_BACKEND_URL="" \
  "$PROJECT_ROOT/FrontEnd"

# ── Deploy based on ENV_MODE ─────────────────────────────
case "$ENV_MODE" in

  k8s-local)
    # Detect OS to select kubectl binary and storageClass
    OS="$(uname -s)"
    case "$OS" in
      Linux)
        KUBECTL="sudo k3s kubectl"
        STORAGE_CLASS="local-path"
        echo ">>> OS=Linux (k3s)  storageClass=$STORAGE_CLASS"

        echo ">>> Importing images into k3s..."
        docker save smart_scheduler_backend:latest  | sudo k3s ctr images import -
        docker save smart_scheduler_frontend:latest | sudo k3s ctr images import -
        ;;
      Darwin|MINGW*|MSYS*|CYGWIN*)
        KUBECTL="kubectl"
        STORAGE_CLASS="hostpath"
        echo ">>> OS=$OS (Docker Desktop)  storageClass=$STORAGE_CLASS"
        # Docker Desktop shares the daemon; no image import needed
        ;;
      *)
        echo "ERROR: Unsupported OS '$OS'"
        exit 1
        ;;
    esac

    # Generate storage patch at runtime (gitignored)
    cat > "$SCRIPT_DIR/k8s/overlays/k8s-local/storage-patch.yaml" <<EOF
- op: replace
  path: /spec/storageClassName
  value: $STORAGE_CLASS
EOF

    echo ">>> Applying K8s manifests..."
    $KUBECTL apply -k "$SCRIPT_DIR/k8s/overlays/k8s-local"

    echo ">>> Creating secrets from .env..."
    $KUBECTL create secret generic app-secret \
      --from-literal=MYSQL_ROOT_PASSWORD="$MYSQL_PASSWORD" \
      --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
      --from-literal=DB_URL="mysql+pymysql://root:${MYSQL_PASSWORD}@mysql-svc:3306/${MYSQL_DATABASE}" \
      --namespace=smart-scheduler \
      --dry-run=client -o yaml | $KUBECTL apply -f -

    echo ">>> Creating mysql-initdb ConfigMap..."
    $KUBECTL create configmap mysql-initdb \
      --from-file="$SCRIPT_DIR/sql/nus_event.sql" \
      --namespace=smart-scheduler \
      --dry-run=client -o yaml | $KUBECTL apply -f -

    echo ">>> Waiting for rollout..."
    $KUBECTL rollout status deployment/mysql    -n smart-scheduler --timeout=120s
    $KUBECTL rollout status deployment/backend  -n smart-scheduler --timeout=120s
    $KUBECTL rollout status deployment/frontend -n smart-scheduler --timeout=120s

    echo ">>> Done!"
    $KUBECTL get pods -n smart-scheduler
    echo ""
    echo "Access: $KUBECTL port-forward -n smart-scheduler svc/frontend-svc 8080:80"
    ;;

  docker)
    echo ">>> Starting with Docker Compose (production)..."
    cd "$SCRIPT_DIR"
    docker compose up -d --build
    echo ">>> Done! Frontend: http://localhost  Backend: http://localhost:8000/docs"
    ;;

  cloud)
    # ── Cloud K8s (EKS/GKE) ──
    # Before enabling:
    #   1. Update env-config.yaml → envs.cloud-sample: domain, imageRegistry
    #   2. Update overlays/cloud/kustomization.yaml patch values accordingly
    #   3. Confirm kubectl context points to cloud cluster:
    #      kubectl config current-context
    # Then uncomment the block below:
    #
    # echo ">>> Pushing images..."
    # docker tag smart_scheduler_backend:latest  "$REGISTRY_URL/backend:latest"
    # docker push "$REGISTRY_URL/backend:latest"
    # docker tag smart_scheduler_frontend:latest "$REGISTRY_URL/frontend:latest"
    # docker push "$REGISTRY_URL/frontend:latest"
    # echo ">>> Applying K8s manifests..."
    # kubectl apply -k "$SCRIPT_DIR/k8s/overlays/cloud"
    echo ">>> Cloud deployment not yet configured. See comments in deploy.sh and env-config.yaml."
    exit 1
    ;;

  *)
    echo "ERROR: Unknown ENV_MODE '$ENV_MODE'. Use: k8s-local | docker | cloud"
    exit 1
    ;;
esac