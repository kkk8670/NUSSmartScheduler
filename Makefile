# Makefile

COMPOSE_DIR      := deployment
COMPOSE_FILE     := docker-compose.yaml
DEV_COMPOSE_FILE := docker-compose.dev.yaml
MONITORING_DIR   := deployment/k8s/monitoring

# 本地 kubectl 和 storageClass（只用于本地 K8s 命令）
ifeq ($(shell uname -s), Linux)
  KUBECTL               := sudo k3s kubectl
  STORAGE_CLASS         := local-path
  NODE_EXPORTER_ENABLED := true
else
  KUBECTL               := kubectl
  STORAGE_CLASS         := hostpath
  NODE_EXPORTER_ENABLED := false
endif

# 云端固定值
CLOUD_STORAGE_CLASS         := standard-rwo
CLOUD_NODE_EXPORTER_ENABLED := true

.PHONY: help init-env infra dev prod down clean status \
        open-frontend open-backend open-grafana open-prometheus \
        monitoring monitoring-cloud monitoring-down \
        grafana

help:
	@echo "Smart Scheduler — 常用命令"
	@echo ""
	@echo "本地开发（Docker Compose）："
	@echo "  make infra              只起 MySQL + Weaviate，代码本地跑"
	@echo "  make dev                MySQL + Weaviate + 后端进 Docker，前端本地跑"
	@echo "  make prod               全部打包成镜像运行"
	@echo "  make down               停止容器（保留数据）"
	@echo "  make clean              停止容器并删除数据卷 ⚠️"
	@echo "  make status             查看容器状态"
	@echo ""
	@echo "K8s 访问（deploy.sh 跑完后执行，保持终端不关）："
	@echo "  make open-frontend      http://localhost:8080"
	@echo "  make open-backend       http://localhost:8000/docs  (账号: user@example.com / string)"
	@echo "  make open-grafana       http://localhost:3000       (账号: admin / smart-scheduler-admin)"
	@echo "  make open-prometheus    http://localhost:9090"
	@echo ""
	@echo "监控（K8s）："
	@echo "  make monitoring         本地 K8s：部署/更新 Prometheus + Grafana + Loki"
	@echo "  make monitoring-cloud   GKE 云端：部署/更新 Prometheus + Grafana + Loki"
	@echo "  make monitoring-down    卸载监控栈（本地或云端，应用不受影响）"

# ── 内部：确保 deployment/.env 软链存在 ─────────────────────────────────────
init-env:
	@cd $(COMPOSE_DIR) && [ -L .env ] || ln -s ../.env .env

# ── 本地开发（Docker Compose）────────────────────────────────────────────────

infra: init-env
	cd $(COMPOSE_DIR) && docker compose up db weaviate -d

dev: init-env
	cd $(COMPOSE_DIR) && docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) up -d

prod: init-env
	cd $(COMPOSE_DIR) && docker compose up --build -d
	@echo "✅ 运行中："
	@echo "   Frontend: http://localhost"
	@echo "   Backend:  http://localhost:8000/docs"

down:
	cd $(COMPOSE_DIR) && docker compose down

clean:
	cd $(COMPOSE_DIR) && docker compose down -v

status:
	cd $(COMPOSE_DIR) && docker compose ps

# ── K8s 访问（port-forward，保持终端不关）────────────────────────────────────

open-frontend:
	@echo ">>> Frontend: http://localhost:8080  (Ctrl+C 停止)"
	$(KUBECTL) port-forward -n smart-scheduler svc/frontend-svc 8080:80

open-backend:
	@echo ">>> Backend API docs: http://localhost:8000/docs"
	@echo "    账号: user@example.com  密码: string"
	@echo "    (Ctrl+C 停止)"
	$(KUBECTL) port-forward -n smart-scheduler svc/backend-svc 8000:8000

open-grafana:
	@echo ">>> Grafana: http://localhost:3000"
	@echo "    账号: admin  密码: smart-scheduler-admin"
	@echo "    (Ctrl+C 停止)"
	$(KUBECTL) port-forward -n monitoring svc/kube-prom-grafana 3000:80

open-prometheus:
	@echo ">>> Prometheus: http://localhost:9090  (Ctrl+C 停止)"
	$(KUBECTL) port-forward -n monitoring svc/kube-prom-kube-prometheus-prometheus 9090:9090

# ── 监控共用逻辑（内部用，不直接调用）───────────────────────────────────────
define deploy_monitoring
	$(1) apply -f $(MONITORING_DIR)/00-namespace.yaml
	$(1) apply -f $(MONITORING_DIR)/20-network-policy.yaml
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
	helm repo add grafana              https://grafana.github.io/helm-charts             2>/dev/null || true
	helm repo update
	@helm status kube-prom -n monitoring --output json 2>/dev/null | \
	  python3 -c "import sys,json; s=json.load(sys.stdin)['info']['status']; exit(0) if s=='deployed' else exit(1)" \
	  || (helm uninstall kube-prom -n monitoring 2>/dev/null || true)
	@helm status loki -n monitoring --output json 2>/dev/null | \
	  python3 -c "import sys,json; s=json.load(sys.stdin)['info']['status']; exit(0) if s=='deployed' else exit(1)" \
	  || (helm uninstall loki -n monitoring 2>/dev/null || true)
	helm upgrade --install kube-prom prometheus-community/kube-prometheus-stack \
	  --namespace monitoring \
	  --values $(MONITORING_DIR)/helm-prometheus-values.yaml \
	  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=$(2) \
	  --set nodeExporter.enabled=$(3) \
	  --timeout 10m --wait
	helm upgrade --install loki grafana/loki-stack \
	  --namespace monitoring \
	  --values $(MONITORING_DIR)/helm-loki-values.yaml \
	  --set loki.persistence.storageClassName=$(2) \
	  --timeout 10m --wait
	$(1) apply -f $(MONITORING_DIR)/10-servicemonitor.yaml
endef

# ── 监控：本地 K8s ────────────────────────────────────────────────────────────
monitoring:
	@echo ">>> [Local] 部署/更新监控栈 (storageClass: $(STORAGE_CLASS))..."
	$(call deploy_monitoring,$(KUBECTL),$(STORAGE_CLASS),$(NODE_EXPORTER_ENABLED))
	@echo "✅ 监控部署完成。运行 make open-grafana 访问 Grafana。"

# ── 监控：GKE 云端 ────────────────────────────────────────────────────────────
# ~/.kube/config 需已指向 GKE 集群（gcloud container clusters get-credentials）
monitoring-cloud:
	@echo ">>> [Cloud] 部署/更新监控栈 (storageClass: $(CLOUD_STORAGE_CLASS))..."
	$(call deploy_monitoring,kubectl,$(CLOUD_STORAGE_CLASS),$(CLOUD_NODE_EXPORTER_ENABLED))
	@echo "✅ 监控部署完成。运行 make open-grafana 访问 Grafana（需 port-forward）。"

# ── 监控：卸载（本地和云端通用）─────────────────────────────────────────────
monitoring-down:
	@echo ">>> 卸载监控栈..."
	helm uninstall loki      --namespace monitoring 2>/dev/null || true
	helm uninstall kube-prom --namespace monitoring 2>/dev/null || true
	$(KUBECTL) delete -f $(MONITORING_DIR)/10-servicemonitor.yaml 2>/dev/null || true
	$(KUBECTL) delete -f $(MONITORING_DIR)/20-network-policy.yaml 2>/dev/null || true
	$(KUBECTL) delete namespace monitoring 2>/dev/null || true
	@echo "✅ 监控已卸载，应用不受影响。"

# 保留旧别名，向后兼容
grafana: open-grafana