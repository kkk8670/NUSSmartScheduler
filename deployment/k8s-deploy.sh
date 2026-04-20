#!/usr/bin/env bash
# deploy.sh – Build & deploy Smart Scheduler
# Reads ENV_MODE from .env to decide deployment target

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
MONITORING_DIR="$SCRIPT_DIR/k8s/monitoring"

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

# ══════════════════════════════════════════════════════════
# deploy_monitoring
# 参数：
#   $1 = kubectl 命令
#   $2 = storageClassName
#   $3 = node-exporter 是否启用（"true" 或 "false"）
#        Linux(k3s) 传 true，Mac/Win(Docker Desktop) 传 false
#        原因：Docker Desktop 的虚拟机层不支持 node-exporter 需要的 mount 方式
# ══════════════════════════════════════════════════════════
deploy_monitoring() {
  local KUBECTL="$1"
  local STORAGE_CLASS="$2"
  local NODE_EXPORTER_ENABLED="$3"   # ← 新增第三个参数

  echo ""
  echo ">>> [Monitoring] Applying monitoring namespace..."
  $KUBECTL apply -f "$MONITORING_DIR/00-namespace.yaml"

  echo ">>> [Monitoring] Applying NetworkPolicy..."
  $KUBECTL apply -f "$MONITORING_DIR/20-network-policy.yaml"

  # ── 检查 helm 是否可用 ────────────────────────────────
  if ! command -v helm &>/dev/null; then
    echo "WARNING: helm not found. Skipping Prometheus/Loki install."
    echo "         Install helm: https://helm.sh/docs/intro/install/"
    echo "         Then re-run deploy.sh to complete monitoring setup."
    return
  fi

  echo ">>> [Monitoring] Adding Helm repos..."
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
  helm repo add grafana              https://grafana.github.io/helm-charts             2>/dev/null || true
  helm repo update

  # ── 检查上次是否安装失败，失败则先清理再重装 ──────────
  # 原因：helm upgrade 对 failed 状态的 release 会报错，必须先 uninstall
  if helm status kube-prom -n monitoring &>/dev/null; then
    HELM_STATUS=$(helm status kube-prom -n monitoring --output json \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['status'])")
    if [ "$HELM_STATUS" != "deployed" ]; then
      echo ">>> [Monitoring] Previous kube-prom status: $HELM_STATUS. Cleaning up..."
      helm uninstall kube-prom -n monitoring 2>/dev/null || true
    fi
  fi

  if helm status loki -n monitoring &>/dev/null; then
    HELM_STATUS=$(helm status loki -n monitoring --output json \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['status'])")
    if [ "$HELM_STATUS" != "deployed" ]; then
      echo ">>> [Monitoring] Previous loki status: $HELM_STATUS. Cleaning up..."
      helm uninstall loki -n monitoring 2>/dev/null || true
    fi
  fi

  echo ">>> [Monitoring] Installing kube-prometheus-stack (Prometheus + Grafana)..."
  helm upgrade --install kube-prom prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    --values "$MONITORING_DIR/helm-prometheus-values.yaml" \
    --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName="$STORAGE_CLASS" \
    --set nodeExporter.enabled="$NODE_EXPORTER_ENABLED" \
    --timeout 10m \
    --wait

  echo ">>> [Monitoring] Installing loki-stack (Loki + Promtail)..."
  helm upgrade --install loki grafana/loki-stack \
    --namespace monitoring \
    --values "$MONITORING_DIR/helm-loki-values.yaml" \
    --set loki.persistence.storageClassName="$STORAGE_CLASS" \
    --timeout 10m \
    --wait

  # ServiceMonitor 必须在 helm install 之后 apply
  # 原因：ServiceMonitor 是 Prometheus Operator 的 CRD，
  # helm install 才会注册这个 CRD，apply 必须在它之后
  echo ">>> [Monitoring] Applying ServiceMonitor (after CRD is ready)..."
  $KUBECTL apply -f "$MONITORING_DIR/10-servicemonitor.yaml"

  echo ""
  echo "✅ Monitoring stack deployed."
  echo "   Access Grafana:"
  echo "     $KUBECTL port-forward -n monitoring svc/kube-prom-grafana 3000:80"
  echo "   Then open: http://localhost:3000  (admin / smart-scheduler-admin)"
  echo ""
  echo "   Default datasources auto-configured:"
  echo "     Prometheus → http://kube-prom-kube-prometheus-prometheus:9090"
  echo "     Loki       → http://loki:3100"
}

# ── Deploy based on ENV_MODE ─────────────────────────────
case "$ENV_MODE" in

  k8s-local)
    OS="$(uname -s)"
    case "$OS" in
      Linux)
        KUBECTL="sudo k3s kubectl"
        STORAGE_CLASS="local-path"
        NODE_EXPORTER_ENABLED="true"    # ← 新增：Linux 支持 node-exporter
        echo ">>> OS=Linux (k3s)  storageClass=$STORAGE_CLASS"

        echo ">>> Importing images into k3s..."
        docker save smart_scheduler_backend:latest  | sudo k3s ctr images import -
        docker save smart_scheduler_frontend:latest | sudo k3s ctr images import -
        ;;
      Darwin|MINGW*|MSYS*|CYGWIN*)
        KUBECTL="kubectl"
        STORAGE_CLASS="hostpath"
        NODE_EXPORTER_ENABLED="false"   # ← 新增：Mac/Win Docker Desktop 不支持
        echo ">>> OS=$OS (Docker Desktop)  storageClass=$STORAGE_CLASS"
        ;;
      *)
        echo "ERROR: Unsupported OS '$OS'"
        exit 1
        ;;
    esac

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

    # NODE_EXPORTER_ENABLED 作为第三个参数传入
    deploy_monitoring "$KUBECTL" "$STORAGE_CLASS" "$NODE_EXPORTER_ENABLED"
    ;;

  docker)
    echo ">>> Starting with Docker Compose (production)..."
    cd "$SCRIPT_DIR"
    docker compose up -d --build
    echo ">>> Done! Frontend: http://localhost  Backend: http://localhost:8000/docs"
    ;;

  cloud)
    # KUBECTL="kubectl"
    # STORAGE_CLASS="gp3"
    # NODE_EXPORTER_ENABLED="true"
    # deploy_monitoring "$KUBECTL" "$STORAGE_CLASS" "$NODE_EXPORTER_ENABLED"
    echo ">>> Cloud deployment not yet configured. See comments in deploy.sh."
    exit 1
    ;;

  *)
    echo "ERROR: Unknown ENV_MODE '$ENV_MODE'. Use: k8s-local | docker | cloud"
    exit 1
    ;;
esac