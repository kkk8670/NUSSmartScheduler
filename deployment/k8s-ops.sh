#!/usr/bin/env bash
# k8s-ops.sh — 停止 / 清理 Smart Scheduler
# 用法：
#   bash deployment/k8s-ops.sh stop          暂停所有 Pod，保留数据
#   bash deployment/k8s-ops.sh start         恢复已暂停的 Pod
#   bash deployment/k8s-ops.sh clean-app     删除应用（数据丢失），保留监控
#   bash deployment/k8s-ops.sh clean-all     删除应用 + 监控，全部清除
#   bash deployment/k8s-ops.sh status        查看所有 Pod 状态

set -euo pipefail

# Mac: kubectl    Linux(k3s): sudo k3s kubectl
if [ "$(uname -s)" = "Linux" ]; then
  KUBECTL="sudo k3s kubectl"
else
  KUBECTL="kubectl"
fi

ACTION="${1:-}"

case "$ACTION" in

  stop)
    echo ">>> Scaling all app deployments to 0 (data preserved)..."
    $KUBECTL scale deployment backend frontend mysql weaviate \
      --replicas=0 -n smart-scheduler 2>/dev/null || true
    echo "✅ All app pods stopped. PVC data is intact."
    echo "   Run 'bash deployment/k8s-ops.sh start' to resume."
    ;;

  start)
    echo ">>> Scaling all app deployments back to 1..."
    $KUBECTL scale deployment backend frontend mysql weaviate \
      --replicas=1 -n smart-scheduler 2>/dev/null || true
    echo "✅ App pods starting. Check status:"
    echo "   bash deployment/k8s-ops.sh status"
    ;;

  clean-app)
    echo ">>> WARNING: This will DELETE the smart-scheduler namespace."
    echo "    All app data (MySQL, Weaviate) will be permanently lost."
    read -p "    Type 'yes' to confirm: " confirm
    if [ "$confirm" != "yes" ]; then
      echo "Aborted."
      exit 0
    fi
    $KUBECTL delete namespace smart-scheduler --ignore-not-found
    echo "✅ Application namespace deleted. Monitoring stack untouched."
    echo "   Run 'bash deployment/deploy.sh' to redeploy from scratch."
    ;;

  clean-all)
    echo ">>> WARNING: This will DELETE everything — app + monitoring."
    echo "    All data will be permanently lost."
    read -p "    Type 'yes' to confirm: " confirm
    if [ "$confirm" != "yes" ]; then
      echo "Aborted."
      exit 0
    fi
    $KUBECTL delete namespace smart-scheduler --ignore-not-found
    helm uninstall kube-prom --namespace monitoring 2>/dev/null || true
    helm uninstall loki      --namespace monitoring 2>/dev/null || true
    $KUBECTL delete namespace monitoring --ignore-not-found
    echo "✅ Everything removed. Run 'bash deployment/deploy.sh' to start fresh."
    ;;

  status)
    echo "=== smart-scheduler ==="
    $KUBECTL get pods -n smart-scheduler 2>/dev/null || echo "(namespace not found)"
    echo ""
    echo "=== monitoring ==="
    $KUBECTL get pods -n monitoring 2>/dev/null || echo "(namespace not found)"
    ;;

  *)
    echo "Usage: bash deployment/k8s-ops.sh <action>"
    echo ""
    echo "  stop        Pause all Pods (data retained; can be resumed with start)"
    echo "  start       Resume paused Pods"
    echo "  clean-app   Delete the application namespace (data will be lost), keep monitoring"
    echo "  clean-all   Delete everything (data will be lost)"
    echo "  status      Check the status of all Pods"
    ;;

esac