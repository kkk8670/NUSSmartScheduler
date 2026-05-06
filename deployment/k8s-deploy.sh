#!/usr/bin/env bash
# deploy.sh – Build & deploy Smart Scheduler
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MONITORING_DIR="$SCRIPT_DIR/k8s/monitoring"
CLOUD_OVERLAY="$SCRIPT_DIR/k8s/overlays/cloud"

# ── 读取 .env ────────────────────────────────────────────
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a; source "$PROJECT_ROOT/.env"; set +a
fi

# ══════════════════════════════════════════════════════════
# 交互式菜单
# ══════════════════════════════════════════════════════════
echo ""
echo "Smart Scheduler Deploy"
echo "────────────────────────────────"
echo "  1) local   – Docker Desktop / k3s"
echo "  2) cloud   – GKE (HTTP, no TLS)"
echo "  3) cloud   – GKE (HTTPS, needs domain + static IP)"
echo "  4) docker  – Docker Compose only"
echo "────────────────────────────────"
printf "Choose [1-4]: "
read -r CHOICE

case "$CHOICE" in
  1) MODE="local"       ;;
  2) MODE="cloud-http"  ;;
  3) MODE="cloud-https" ;;
  4) MODE="docker"      ;;
  *) echo "Invalid choice."; exit 1 ;;
esac

# cloud-https 追问域名和静态 IP
if [ "$MODE" = "cloud-https" ]; then
  echo ""
  printf "Domain (e.g. scheduler.example.com): "
  read -r CLOUD_DOMAIN
  printf "Static IP name (from: gcloud compute addresses list): "
  read -r CLOUD_STATIC_IP_NAME
fi

# 监控是否部署（docker 模式不适用）
DEPLOY_MONITORING=false
if [ "$MODE" != "docker" ]; then
  echo ""
  printf "Deploy monitoring stack? (Prometheus + Grafana + Loki) [y/N]: "
  read -r MON_CHOICE
  [[ "$MON_CHOICE" =~ ^[Yy]$ ]] && DEPLOY_MONITORING=true
fi

# ══════════════════════════════════════════════════════════
# Build images
# ══════════════════════════════════════════════════════════
if [ "$MODE" != "docker" ]; then
  echo ""
  echo ">>> Building images..."
  docker system prune -f
  docker build -t smart_scheduler_backend:1.0.0 "$PROJECT_ROOT/BackEnd"
  docker build -t smart_scheduler_frontend:1.0.0 \
    --build-arg VITE_BACKEND_URL="" \
    "$PROJECT_ROOT/FrontEnd"
fi

# ══════════════════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════════════════
apply_secrets() {
  local KUBECTL="$1"
  echo ">>> Creating/updating app-secret..."
  $KUBECTL create secret generic app-secret \
    --from-literal=MYSQL_ROOT_PASSWORD="${MYSQL_PASSWORD}" \
    --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY}" \
    --from-literal=DB_URL="mysql+pymysql://root:${MYSQL_PASSWORD}@mysql-svc:3306/${MYSQL_DATABASE}" \
    --from-literal=LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-}" \
    --from-literal=LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-}" \
    --from-literal=LANGFUSE_BASE_URL="${LANGFUSE_BASE_URL:-https://us.cloud.langfuse.com}" \
    --namespace=smart-scheduler \
    --dry-run=client -o yaml | $KUBECTL apply -f -

  echo ">>> Creating/updating mysql-initdb configmap..."
  $KUBECTL create configmap mysql-initdb \
    --from-file="$SCRIPT_DIR/sql/nus_event.sql" \
    --namespace=smart-scheduler \
    --dry-run=client -o yaml | $KUBECTL apply -f -
}

wait_rollout() {
  local KUBECTL="$1"
  local TIMEOUT="$2"
  echo ">>> Waiting for rollout..."
  $KUBECTL rollout status deployment/mysql    -n smart-scheduler --timeout="${TIMEOUT}"
  $KUBECTL rollout status deployment/weaviate -n smart-scheduler --timeout="${TIMEOUT}"
  $KUBECTL rollout status deployment/backend  -n smart-scheduler --timeout="${TIMEOUT}"
  $KUBECTL rollout status deployment/frontend -n smart-scheduler --timeout="${TIMEOUT}"
}

push_images() {
  local REGISTRY="$1"
  local IMAGE_TAG="$2"
  echo ">>> Pushing images (tag: $IMAGE_TAG)..."
  gcloud auth configure-docker asia-southeast1-docker.pkg.dev --quiet
  docker tag smart_scheduler_backend:1.0.0  "$REGISTRY/backend:$IMAGE_TAG"
  docker tag smart_scheduler_frontend:1.0.0 "$REGISTRY/frontend:$IMAGE_TAG"
  docker push "$REGISTRY/backend:$IMAGE_TAG"
  docker push "$REGISTRY/frontend:$IMAGE_TAG"

  ( cd "$CLOUD_OVERLAY"
    kustomize edit set image \
      "smart_scheduler_backend=$REGISTRY/backend:$IMAGE_TAG" \
      "smart_scheduler_frontend=$REGISTRY/frontend:$IMAGE_TAG" )
}

deploy_monitoring() {
  local KUBECTL="$1"
  local STORAGE_CLASS="$2"
  local NODE_EXPORTER="$3"

  if [ "$DEPLOY_MONITORING" = false ]; then
    echo ""
    echo ">>> Skipping monitoring stack."
    echo "    Run 'make monitoring' later when ready."
    return
  fi

  echo ""
  echo ">>> [Monitoring] Applying namespace + NetworkPolicy..."
  $KUBECTL apply -f "$MONITORING_DIR/00-namespace.yaml"
  $KUBECTL apply -f "$MONITORING_DIR/20-network-policy.yaml"

  if ! command -v helm &>/dev/null; then
    echo "WARNING: helm not found, skipping Prometheus/Loki."
    echo "         Install helm and run 'make monitoring' to deploy later."
    return
  fi

  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
  helm repo add grafana https://grafana.github.io/helm-charts 2>/dev/null || true
  helm repo update

  for release in kube-prom loki; do
    if helm status "$release" -n monitoring &>/dev/null; then
      STATUS=$(helm status "$release" -n monitoring --output json \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['status'])")
      if [ "$STATUS" != "deployed" ]; then
        helm uninstall "$release" -n monitoring 2>/dev/null || true
      fi
    fi
  done

  echo ">>> [Monitoring] Installing kube-prometheus-stack..."
  helm upgrade --install kube-prom prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    --values "$MONITORING_DIR/helm-prometheus-values.yaml" \
    --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName="$STORAGE_CLASS" \
    --set nodeExporter.enabled="$NODE_EXPORTER" \
    --set grafana."grafana\.ini".smtp.password="${GRAFANA_SMTP_PASSWORD:-}" \
    --set grafana."grafana\.ini".smtp.user="${GRAFANA_SMTP_USER:-}" \
    --timeout 10m --wait

  echo ">>> [Monitoring] Installing loki-stack..."
  helm upgrade --install loki grafana/loki-stack \
    --namespace monitoring \
    --values "$MONITORING_DIR/helm-loki-values.yaml" \
    --set loki.persistence.storageClassName="$STORAGE_CLASS" \
    --timeout 10m --wait

  $KUBECTL apply -f "$MONITORING_DIR/10-servicemonitor.yaml"
  echo "✅ Monitoring deployed. Run 'make open-grafana' to access Grafana."
}

# ══════════════════════════════════════════════════════════
# 部署逻辑
# ══════════════════════════════════════════════════════════
case "$MODE" in

  # ── 1) Local ────────────────────────────────────────────
  local)
    OS="$(uname -s)"
    case "$OS" in
      Linux)
        KUBECTL="sudo k3s kubectl"
        STORAGE_CLASS="local-path"
        NODE_EXPORTER="true"
        docker save smart_scheduler_backend:1.0.0  | sudo k3s ctr images import -
        docker save smart_scheduler_frontend:1.0.0 | sudo k3s ctr images import -
        ;;
      Darwin|MINGW*|MSYS*|CYGWIN*)
        KUBECTL="kubectl"
        STORAGE_CLASS="hostpath"
        NODE_EXPORTER="false"
        ;;
      *) echo "Unsupported OS: $OS"; exit 1 ;;
    esac

    cat > "$SCRIPT_DIR/k8s/overlays/k8s-local/storage-patch.yaml" <<EOF
- op: replace
  path: /spec/storageClassName
  value: $STORAGE_CLASS
EOF

    apply_secrets "$KUBECTL"

    echo ">>> Applying manifests (local)..."
    $KUBECTL apply -k "$SCRIPT_DIR/k8s/overlays/k8s-local"
    wait_rollout "$KUBECTL" "120s"

    echo ""
    echo "✅ Application is running."
    echo "   Run 'make open-frontend' to access the app."
    deploy_monitoring "$KUBECTL" "$STORAGE_CLASS" "$NODE_EXPORTER"
    ;;

  # ── 2) Cloud HTTP ───────────────────────────────────────
  cloud-http)
    REGISTRY="asia-southeast1-docker.pkg.dev/nus-smart-scheduler/smart-scheduler"
    IMAGE_TAG="${GITHUB_SHA:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"

    push_images "$REGISTRY" "$IMAGE_TAG"

    apply_secrets "kubectl"

    echo ">>> Applying manifests (cloud, HTTP)..."
    kubectl apply -k "$CLOUD_OVERLAY"
    wait_rollout "kubectl" "300s"

    echo ""
    echo "✅ Application is running."
    INGRESS_IP=$(kubectl get ingress smart-scheduler-ingress -n smart-scheduler \
      -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    echo "   Access: http://$INGRESS_IP"
    deploy_monitoring "kubectl" "standard-rwo" "true"
    ;;

  # ── 3) Cloud HTTPS ──────────────────────────────────────
  cloud-https)
    REGISTRY="asia-southeast1-docker.pkg.dev/nus-smart-scheduler/smart-scheduler"
    IMAGE_TAG="${GITHUB_SHA:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"

    push_images "$REGISTRY" "$IMAGE_TAG"

    RENDERED="$(mktemp -d)"
    trap 'rm -rf "$RENDERED"' EXIT
    cp -r "$CLOUD_OVERLAY/." "$RENDERED/"
    export CLOUD_DOMAIN CLOUD_STATIC_IP_NAME
    envsubst '${CLOUD_DOMAIN} ${CLOUD_STATIC_IP_NAME}' \
      < "$CLOUD_OVERLAY/kustomization.yaml" \
      > "$RENDERED/kustomization.yaml"
    envsubst '${CLOUD_DOMAIN}' \
      < "$CLOUD_OVERLAY/32-gce-ingress-resources.yaml" \
      > "$RENDERED/32-gce-ingress-resources.yaml"

    apply_secrets "kubectl"

    echo ">>> Applying manifests (cloud, HTTPS, domain: $CLOUD_DOMAIN)..."
    kubectl apply -k "$RENDERED"
    wait_rollout "kubectl" "300s"

    echo ""
    echo "✅ Application is running."
    echo "   Access: https://$CLOUD_DOMAIN"
    echo "   Certificate provisioning takes 10-60 min:"
    kubectl get managedcertificate -n smart-scheduler 2>/dev/null || true
    deploy_monitoring "kubectl" "standard-rwo" "true"
    ;;

  # ── 4) Docker Compose ───────────────────────────────────
  docker)
    echo ">>> Starting with Docker Compose..."
    cd "$SCRIPT_DIR"
    docker compose up -d --build
    echo "✅ Done. Frontend: http://localhost  Backend: http://localhost:8000/docs"
    ;;

esac