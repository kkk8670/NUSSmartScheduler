#!/usr/bin/env bash
# k8s-ops.sh — 日常维护 Smart Scheduler
# 用法：bash deployment/k8s-ops.sh <action>

set -euo pipefail

if [ "$(uname -s)" = "Linux" ]; then
  KUBECTL="sudo k3s kubectl"
else
  KUBECTL="kubectl"
fi

ACTION="${1:-}"

case "$ACTION" in

  status)
    echo "=== smart-scheduler ==="
    $KUBECTL get pods -n smart-scheduler 2>/dev/null || echo "(namespace not found)"
    echo ""
    echo "=== PVC ==="
    $KUBECTL get pvc -n smart-scheduler 2>/dev/null || echo "(none)"
    echo ""
    echo "=== Ingress ==="
    $KUBECTL get ingress -n smart-scheduler 2>/dev/null || echo "(none)"
    echo ""
    echo "=== monitoring ==="
    $KUBECTL get pods -n monitoring 2>/dev/null || echo "(namespace not found)"
    ;;

  stop)
    echo ">>> Scaling all app deployments to 0 (data preserved)..."
    $KUBECTL scale deployment backend frontend mysql weaviate \
      --replicas=0 -n smart-scheduler 2>/dev/null || true
    echo "✅ All app pods stopped. PVC data is intact."
    echo "   Run: bash deployment/k8s-ops.sh start"
    ;;

  start)
    echo ">>> Scaling all app deployments back to 1..."
    $KUBECTL scale deployment backend frontend mysql weaviate \
      --replicas=1 -n smart-scheduler 2>/dev/null || true
    echo "✅ App pods starting."
    echo "   Run: bash deployment/k8s-ops.sh status"
    ;;

  reset-weaviate)
    echo ">>> WARNING: This will clear all Weaviate vector data."
    echo "    Use this when Weaviate is stuck trying to join an old cluster."
    printf "    Type 'yes' to confirm: "
    read -r confirm
    if [ "$confirm" != "yes" ]; then echo "Aborted."; exit 0; fi

    echo ">>> Scaling down Weaviate..."
    $KUBECTL scale deployment weaviate --replicas=0 -n smart-scheduler

    echo ">>> Waiting for Weaviate Pod to fully stop..."
    $KUBECTL wait --for=delete pod -l app=weaviate       -n smart-scheduler --timeout=60s 2>/dev/null || true

    echo ">>> Clearing PVC data..."
    $KUBECTL run weaviate-reset --image=busybox:1.36 \
      --restart=Never \
      --overrides='{
        "spec": {
          "containers": [{"name":"weaviate-reset","image":"busybox:1.36",
            "command":["sh","-c","rm -rf /data/* && echo cleared && ls /data/"],
            "volumeMounts":[{"name":"data","mountPath":"/data"}]}],
          "volumes":[{"name":"data","persistentVolumeClaim":{"claimName":"weaviate-pvc"}}]
        }
      }' \
      -n smart-scheduler

    $KUBECTL wait pod/weaviate-reset -n smart-scheduler \
      --for=condition=Ready --timeout=30s 2>/dev/null || true
    $KUBECTL logs weaviate-reset -n smart-scheduler
    $KUBECTL delete pod weaviate-reset -n smart-scheduler

    echo ">>> Scaling Weaviate back up..."
    $KUBECTL scale deployment weaviate --replicas=1 -n smart-scheduler
    echo "✅ Weaviate reset. Vector data cleared, re-import if needed."
    ;;

  clean-app)
    echo ">>> WARNING: This will DELETE the smart-scheduler namespace."
    echo "    All app data (MySQL, Weaviate) will be permanently lost."
    printf "    Type 'yes' to confirm: "
    read -r confirm
    if [ "$confirm" != "yes" ]; then echo "Aborted."; exit 0; fi
    $KUBECTL delete namespace smart-scheduler --ignore-not-found
    echo "✅ Application namespace deleted. Monitoring stack untouched."
    echo "   Run: bash deployment/k8s-deploy.sh"
    ;;

  clean-all)
    echo ">>> WARNING: This will DELETE everything — app + monitoring."
    echo "    All data will be permanently lost."
    printf "    Type 'yes' to confirm: "
    read -r confirm
    if [ "$confirm" != "yes" ]; then echo "Aborted."; exit 0; fi
    $KUBECTL delete namespace smart-scheduler --ignore-not-found
    helm uninstall kube-prom --namespace monitoring 2>/dev/null || true
    helm uninstall loki      --namespace monitoring 2>/dev/null || true
    $KUBECTL delete namespace monitoring --ignore-not-found
    echo "✅ Everything removed."
    echo "   Run: bash deployment/k8s-deploy.sh"
    ;;

  *)
    echo "Usage: bash deployment/k8s-ops.sh <action>"
    echo ""
    echo "  status          查看所有 Pod、PVC、Ingress 状态"
    echo "  stop            暂停所有 Pod（数据保留）"
    echo "  start           恢复暂停的 Pod"
    echo "  reset-weaviate  清空 Weaviate 数据（出现集群脏数据时用）"
    echo "  clean-app       删除应用 namespace ⚠️ 数据丢失，监控保留"
    echo "  clean-all       删除应用 + 监控 ⚠️ 全部清空"
    ;;

esac