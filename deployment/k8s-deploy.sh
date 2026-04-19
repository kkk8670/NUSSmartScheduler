#!/usr/bin/env bash
# deploy.sh – Build & deploy Smart Scheduler
# Reads ENV_MODE from .env to decide deployment target
#
# ── 改动说明 ──────────────────────────────────────────────────────────────
# 新增 deploy_monitoring() 函数，在应用部署完成后调用。
# 改动边界清晰：现有的应用部署逻辑（kustomize 部分）完全不动，
# 只在每个 case 分支末尾追加 deploy_monitoring 调用。
#
# ── 为什么在 deploy.sh 里用 helm，而不是另建一个脚本？─────────────────
# deploy.sh 已经是"一键部署"的单一入口，团队成员只需要跑这一个脚本。
# 把监控部署拆成另一个脚本会增加操作步骤和文档维护负担。
# helm install 命令幂等性强（--install 让 upgrade 在首次也能工作），
# 放在同一脚本末尾不会有副作用。
#
# ── storageClass 的动态注入 ───────────────────────────────────────────────
# helm-prometheus-values.yaml 和 helm-loki-values.yaml 里写的是 local-path，
# 在 cloud 环境需要改成 gp3。通过 --set 参数在运行时覆盖，
# 与应用 PVC 的 storage-patch.yaml 保持相同的动态注入思路。

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
# ── [新增] deploy_monitoring：用 Helm 安装 Prometheus + Grafana + Loki
# ══════════════════════════════════════════════════════════
# 参数：
#   $1 = kubectl 命令（"kubectl" 或 "sudo k3s kubectl"）
#   $2 = storageClassName（"local-path" 或 "gp3"）
#
# 为什么先 apply namespace 再 helm install？
#   helm install --namespace monitoring --create-namespace 也能建 namespace，
#   但 00-namespace.yaml 里带有我们自定义的 label，helm 建的 namespace
#   不会有这些 label，后续 NetworkPolicy 的 namespaceSelector 会匹配失败。
#   所以先 kubectl apply namespace，再让 helm 使用已有的 namespace。
#
# 为什么用 helm upgrade --install 而不是 helm install？
#   --install 让这个命令幂等：首次执行是 install，后续执行是 upgrade。
#   同一个 deploy.sh 可以反复执行，不会因为 release 已存在而报错。
deploy_monitoring() {
  local KUBECTL="$1"
  local STORAGE_CLASS="$2"

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

  echo ">>> [Monitoring] Installing kube-prometheus-stack (Prometheus + Grafana)..."
  helm upgrade --install kube-prom prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    --values "$MONITORING_DIR/helm-prometheus-values.yaml" \
    --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName="$STORAGE_CLASS" \
    --timeout 5m \
    --wait

  echo ">>> [Monitoring] Installing loki-stack (Loki + Promtail)..."
  helm upgrade --install loki grafana/loki-stack \
    --namespace monitoring \
    --values "$MONITORING_DIR/helm-loki-values.yaml" \
    --set loki.persistence.storageClassName="$STORAGE_CLASS" \
    --timeout 5m \
    --wait

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
# ══════════════════════════════════════════════════════════

# ── Deploy based on ENV_MODE ─────────────────────────────
case "$ENV_MODE" in

  k8s-local)
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

    # ── [新增] 部署监控栈 ──────────────────────────────────
    deploy_monitoring "$KUBECTL" "$STORAGE_CLASS"
    ;;

  docker)
    echo ">>> Starting with Docker Compose (production)..."
    cd "$SCRIPT_DIR"
    docker compose up -d --build
    echo ">>> Done! Frontend: http://localhost  Backend: http://localhost:8000/docs"
    # Docker Compose 模式不部署监控（只用于本地开发，Langfuse 已足够）
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
    # KUBECTL="kubectl"
    # STORAGE_CLASS="gp3"
    # echo ">>> Pushing images..."
    # docker tag smart_scheduler_backend:latest  "$REGISTRY_URL/backend:latest"
    # docker push "$REGISTRY_URL/backend:latest"
    # docker tag smart_scheduler_frontend:latest "$REGISTRY_URL/frontend:latest"
    # docker push "$REGISTRY_URL/frontend:latest"
    # echo ">>> Applying K8s manifests..."
    # kubectl apply -k "$SCRIPT_DIR/k8s/overlays/cloud"
    # ... secrets / configmap ...
    # deploy_monitoring "$KUBECTL" "$STORAGE_CLASS"   # ← 取消注释启用云端监控
    echo ">>> Cloud deployment not yet configured. See comments in deploy.sh and env-config.yaml."
    exit 1
    ;;

  *)
    echo "ERROR: Unknown ENV_MODE '$ENV_MODE'. Use: k8s-local | docker | cloud"
    exit 1
    ;;
esac