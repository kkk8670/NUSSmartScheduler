# Makefile

# Variables
COMPOSE_DIR      := deployment
COMPOSE_FILE     := docker-compose.yaml
DEV_COMPOSE_FILE := docker-compose.dev.yaml
MONITORING_DIR   := deployment/k8s/monitoring

# ── 自动探测 kubectl 命令（k3s Linux vs Docker Desktop）──────────────────
ifeq ($(shell uname -s), Linux)
  KUBECTL               := sudo k3s kubectl
  STORAGE_CLASS         := local-path
  NODE_EXPORTER_ENABLED := true    # ← 新增：Linux(k3s) 支持 node-exporter
else
  KUBECTL               := kubectl
  STORAGE_CLASS         := hostpath
  NODE_EXPORTER_ENABLED := false   # ← 新增：Mac/Win Docker Desktop 不支持
endif

.PHONY: help init-env infra dev prod down clean status monitoring grafana monitoring-down

help:
	@echo "Smart Scheduler Management Commands:"
	@echo ""
	@echo "  Application:"
	@echo "  make infra           - Start infrastructure only (DB + VectorDB)"
	@echo "  make dev             - Start DB + VectorDB + Backend in Docker (hot-reload)"
	@echo "  make prod            - Full production build (all in Docker)"
	@echo "  make down            - Stop all containers"
	@echo "  make clean           - Stop all containers AND delete volumes"
	@echo "  make status          - Show container status"
	@echo ""
	@echo "  Monitoring (K8s only):"
	@echo "  make monitoring      - Deploy/update Prometheus + Grafana + Loki"
	@echo "  make grafana         - Port-forward Grafana to http://localhost:3000"
	@echo "  make monitoring-down - Uninstall monitoring stack (keep application)"

# Internal task: Ensure .env symlink exists in the deployment folder
init-env:
	@echo "Checking environment configuration..."
	@cd $(COMPOSE_DIR) && [ -L .env ] || ln -s ../.env .env

# ── Application targets ──────────────────────────────────────────────────────

infra: init-env
	cd $(COMPOSE_DIR) && docker compose up db weaviate -d

dev: init-env
	cd $(COMPOSE_DIR) && docker compose -f $(COMPOSE_FILE) -f $(DEV_COMPOSE_FILE) up -d

prod: init-env
	cd $(COMPOSE_DIR) && docker compose up --build -d
	@echo "✅ Production running:"
	@echo "   Frontend: http://localhost"
	@echo "   Backend:  http://localhost:8000/docs"

down:
	cd $(COMPOSE_DIR) && docker compose down

clean:
	cd $(COMPOSE_DIR) && docker compose down -v

status:
	cd $(COMPOSE_DIR) && docker compose ps

# ── Monitoring targets ───────────────────────────────────────────────────────

monitoring:
	@echo ">>> Deploying monitoring stack to K8s..."
	$(KUBECTL) apply -f $(MONITORING_DIR)/00-namespace.yaml
	$(KUBECTL) apply -f $(MONITORING_DIR)/20-network-policy.yaml
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
	helm repo add grafana              https://grafana.github.io/helm-charts             2>/dev/null || true
	helm repo update
	# ── 清理上次失败的 release（状态不是 deployed 时先 uninstall）──
	@helm status kube-prom -n monitoring --output json 2>/dev/null | \
	  python3 -c "import sys,json; s=json.load(sys.stdin)['info']['status']; exit(0) if s=='deployed' else exit(1)" \
	  || (helm uninstall kube-prom -n monitoring 2>/dev/null || true)
	@helm status loki -n monitoring --output json 2>/dev/null | \
	  python3 -c "import sys,json; s=json.load(sys.stdin)['info']['status']; exit(0) if s=='deployed' else exit(1)" \
	  || (helm uninstall loki -n monitoring 2>/dev/null || true)
	# ── 先装 helm chart（注册 CRD），再 apply ServiceMonitor ──
	helm upgrade --install kube-prom prometheus-community/kube-prometheus-stack \
	  --namespace monitoring \
	  --values $(MONITORING_DIR)/helm-prometheus-values.yaml \
	  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=$(STORAGE_CLASS) \
	  --set nodeExporter.enabled=$(NODE_EXPORTER_ENABLED) \
	  --timeout 10m --wait
	helm upgrade --install loki grafana/loki-stack \
	  --namespace monitoring \
	  --values $(MONITORING_DIR)/helm-loki-values.yaml \
	  --set loki.persistence.storageClassName=$(STORAGE_CLASS) \
	  --timeout 10m --wait
	# ── ServiceMonitor 必须在 helm 之后，CRD 才存在 ──
	$(KUBECTL) apply -f $(MONITORING_DIR)/10-servicemonitor.yaml
	@echo "✅ Monitoring deployed. Run 'make grafana' to access dashboard."

grafana:
	@echo ">>> Grafana: http://localhost:3000  (admin / smart-scheduler-admin)"
	@echo "    Press Ctrl+C to stop port-forward"
	$(KUBECTL) port-forward -n monitoring svc/kube-prom-grafana 3000:80

monitoring-down:
	@echo ">>> Uninstalling monitoring stack..."
	helm uninstall loki      --namespace monitoring 2>/dev/null || true
	helm uninstall kube-prom --namespace monitoring 2>/dev/null || true
	$(KUBECTL) delete -f $(MONITORING_DIR)/10-servicemonitor.yaml 2>/dev/null || true
	$(KUBECTL) delete -f $(MONITORING_DIR)/20-network-policy.yaml 2>/dev/null || true
	$(KUBECTL) delete namespace monitoring 2>/dev/null || true
	@echo "✅ Monitoring stack removed. Application is unaffected."