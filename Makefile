# Makefile

# Variables
COMPOSE_DIR      := deployment
COMPOSE_FILE     := docker-compose.yaml
DEV_COMPOSE_FILE := docker-compose.dev.yaml
MONITORING_DIR   := deployment/k8s/monitoring

# ── 自动探测 kubectl 命令（k3s Linux vs Docker Desktop）──────────────────
# 和 deploy.sh 保持相同的探测逻辑
ifeq ($(shell uname -s), Linux)
  KUBECTL        := sudo k3s kubectl
  STORAGE_CLASS  := local-path
else
  KUBECTL        := kubectl
  STORAGE_CLASS  := hostpath
endif

.PHONY: help init infra dev prod down clean status monitoring grafana monitoring-down

# 新增三个 monitoring 相关 target：
#   make monitoring  → 单独部署/更新监控栈（不重新部署应用）
#   make grafana     → port-forward Grafana 到本地 3000 端口
#   make monitoring-down → 卸载监控栈（保留应用）
# 
# 为什么单独提供 make monitoring，而不只依赖 deploy.sh？
#   deploy.sh 每次都重新 build 镜像、import 到 k3s、等待 rollout——
#   只想更新 Helm values 时（比如调整 retention 期限）跑完整 deploy.sh 太慢。
#   make monitoring 只跑 helm upgrade，秒级完成。
#
# 为什么单独提供 make grafana？
#   port-forward 是临时命令，需要保持终端窗口打开，经常需要单独执行。
#   封装成 target 避免记忆长命令。
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

# ── Application targets (原有，不变）────────────────────────────────────────

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

# ── Monitoring targets（新增）────────────────────────────────────────────────

# 单独部署/更新监控栈，不重新 build 应用镜像
# 前提：应用已通过 deploy.sh 部署到 K8s
monitoring:
	@echo ">>> Deploying monitoring stack to K8s..."
	$(KUBECTL) apply -f $(MONITORING_DIR)/00-namespace.yaml
	$(KUBECTL) apply -f $(MONITORING_DIR)/10-servicemonitor.yaml
	$(KUBECTL) apply -f $(MONITORING_DIR)/20-network-policy.yaml
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
	helm repo add grafana              https://grafana.github.io/helm-charts             2>/dev/null || true
	helm repo update
	helm upgrade --install kube-prom prometheus-community/kube-prometheus-stack \
	  --namespace monitoring \
	  --values $(MONITORING_DIR)/helm-prometheus-values.yaml \
	  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=$(STORAGE_CLASS) \
	  --timeout 5m --wait
	helm upgrade --install loki grafana/loki-stack \
	  --namespace monitoring \
	  --values $(MONITORING_DIR)/helm-loki-values.yaml \
	  --set loki.persistence.storageClassName=$(STORAGE_CLASS) \
	  --timeout 5m --wait
	@echo "✅ Monitoring deployed. Run 'make grafana' to access dashboard."

# Port-forward Grafana 到本地（命令会占用终端，Ctrl+C 停止）
grafana:
	@echo ">>> Grafana: http://localhost:3000  (admin / smart-scheduler-admin)"
	@echo "    Press Ctrl+C to stop port-forward"
	$(KUBECTL) port-forward -n monitoring svc/kube-prom-grafana 3000:80

# 卸载监控栈，应用完全不受影响
monitoring-down:
	@echo ">>> Uninstalling monitoring stack..."
	helm uninstall loki     --namespace monitoring 2>/dev/null || true
	helm uninstall kube-prom --namespace monitoring 2>/dev/null || true
	$(KUBECTL) delete -f $(MONITORING_DIR)/20-network-policy.yaml 2>/dev/null || true
	$(KUBECTL) delete -f $(MONITORING_DIR)/10-servicemonitor.yaml 2>/dev/null || true
	$(KUBECTL) delete namespace monitoring 2>/dev/null || true
	@echo "✅ Monitoring stack removed. Application is unaffected."