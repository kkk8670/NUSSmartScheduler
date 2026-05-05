# Smart Scheduler — Deployment Guide

## 目录

- [整体架构](#整体架构)
- [前置准备](#前置准备)
- [日常开发（本地）](#日常开发本地)
- [K8s 本地部署](#k8s-本地部署)
- [K8s 云端部署 GKE](#k8s-云端部署-gke)
- [访问服务](#访问服务)
- [监控](#监控)
- [日常维护](#日常维护)
- [CI/CD](#cicd)
- [文件结构说明](#文件结构说明)
- [后端本地测试](#后端本地测试)

---

## 整体架构

```
本地开发              K8s 本地              K8s 云端 (GKE)
─────────────         ──────────────        ──────────────────────
make infra/dev   →    bash deploy.sh   →    bash deploy.sh
Docker Compose        Docker Desktop         GKE asia-southeast1
                      或 k3s (Linux)         scheduler-cluster
```

三种模式都从同一份代码启动，`deploy.sh` 交互式菜单选择目标。

---

## 前置准备

**每台机器只做一次。**

### 1. 基础工具

```bash
# Helm（K8s 监控栈需要）
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

### 2. K8s 环境（本地）

**Mac / Windows**
Docker Desktop → Settings → Kubernetes → ✅ Enable Kubernetes → Apply & Restart
等左下角状态变绿（约 1-2 分钟）。

**Linux**
```bash
curl -sfL https://get.k3s.io | sh -
sudo k3s kubectl get nodes   # 验证
```

### 3. 配置 .env

```bash
cp .env.example .env
```

必填项：

| 字段 | 说明 |
|------|------|
| `MYSQL_PASSWORD` | 数据库密码，自己定 |
| `MYSQL_DATABASE` | 固定填 `nus_event` |
| `OPENAI_API_KEY` | OpenAI key |

可选项（不填则对应功能禁用）：

| 字段 | 说明 |
|------|------|
| `LANGFUSE_PUBLIC_KEY` | Langfuse tracing |
| `LANGFUSE_SECRET_KEY` | Langfuse tracing |
| `GRAFANA_SMTP_USER` | 邮件告警 |
| `GRAFANA_SMTP_PASSWORD` | 邮件告警 |

---

## 日常开发（本地）

本地开发不走 K8s，用 Docker Compose 起基础设施，代码在本机热更新。

### 首次进入

```bash
cd deployment && ln -s ../.env .env      # 给 compose 用的 .env 软链

cd BackEnd
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cd FrontEnd && npm install
```

### 启动

**模式一：只起数据库 + Weaviate，代码全部本地跑（最常用）**

```bash
make infra

# 终端 1 — 后端
cd BackEnd && uvicorn main:app --reload
# 访问: http://localhost:8000/docs

# 终端 2 — 前端
cd FrontEnd && npm run dev
# 访问: http://localhost:5173
```

**模式二：后端也进 Docker（热更新），前端本地跑**

```bash
make dev
cd FrontEnd && npm run dev   # 前端仍在本地，http://localhost:5173
```

**模式三：全部打包成镜像运行**

```bash
make prod
# Frontend: http://localhost
# Backend:  http://localhost:8000/docs
```

### 停止

```bash
make down      # 停容器，保留数据
make clean     # 停容器，删除数据卷（⚠️ 数据清空）
```

---

## K8s 本地部署

用于验证 K8s 配置，行为和云端一致。

```bash
bash deployment/k8s-deploy.sh
# 菜单选 1 (local)
```

deploy.sh 自动完成以下步骤，**完成后停在"所有 Pod Running"这一步**：

```
build 镜像
  → import 到集群
    → kubectl apply manifests（创建 namespace、Pod、Service、NetworkPolicy）
      → kubectl create secret（注入数据库密码、API key）
        → 等待所有 Pod 变成 Running
          → 部署监控栈（Prometheus + Grafana + Loki）
            → 结束 ✅
```

**deploy 结束不等于可以访问。** K8s 的 Pod 只在集群内网里运行，外面访问不到，就像服务器上起了进程但防火墙没开。`make open-*` 命令（见下方[访问服务](#访问服务)）会打开临时通道把集群端口映射到本地。云端部署有 Ingress + 公网 IP，不需要这步。

**重新部署**（代码有更新时）：

```bash
bash deployment/k8s-deploy.sh   # 再选 1，幂等，直接覆盖
```

**只更新单个服务**（不想重新 build 所有镜像）：

```bash
# 以后端为例
docker build -t smart_scheduler_backend:1.0.0 ./BackEnd

# Mac（Docker Desktop 共享 daemon，无需 import）
kubectl rollout restart deployment/backend -n smart-scheduler

# Linux (k3s)
docker save smart_scheduler_backend:1.0.0 | sudo k3s ctr images import -
sudo k3s kubectl rollout restart deployment/backend -n smart-scheduler
```

---

## K8s 云端部署 (GKE)

### 首次准备（只做一次）

**1. 安装 gcloud CLI**
https://cloud.google.com/sdk/docs/install

**2. 登录并创建集群**

```bash
gcloud auth login
gcloud config set project nus-smart-scheduler

gcloud container clusters create scheduler-cluster \
  --region asia-southeast1 \
  --machine-type e2-medium \
  --num-nodes 2

# 拉取集群凭据到本地（写入 ~/.kube/config，之后 kubectl 才能用）
gcloud container clusters get-credentials scheduler-cluster \
  --region asia-southeast1 \
  --project nus-smart-scheduler
```

**3. 创建 Artifact Registry 仓库**

```bash
gcloud artifacts repositories create smart-scheduler \
  --repository-format=docker \
  --location=asia-southeast1
```

**4. 团队其他成员加入**

被加到 GCP 项目 IAM 后，自己跑一次：

```bash
gcloud auth login
gcloud container clusters get-credentials scheduler-cluster \
  --region asia-southeast1 --project nus-smart-scheduler
```

### 部署

```bash
bash deployment/k8s-deploy.sh
# 菜单选 2 (cloud HTTP) 或 3 (cloud HTTPS)
```

**选 2 — HTTP（推荐先用）**
不需要域名，GKE 自动分配外部 IP，部署完脚本打印访问地址。

**选 3 — HTTPS**
需要域名 + 静态 IP，脚本会交互式询问：
```
Domain (e.g. scheduler.example.com): your.domain.com
Static IP name (from: gcloud compute addresses list): scheduler-static-ip
```
证书由 GCP 自动签发，首次需 10-60 分钟，期间 HTTPS 报证书错误属正常。

云端部署完成后直接用公网 IP 访问，**不需要 port-forward**。

---

## 访问服务

### 本地 K8s

deploy.sh 跑完后，在新终端执行以下命令，**保持终端窗口不关**（关掉就断了）：

```bash
make open-frontend     # http://localhost:8080
make open-backend      # http://localhost:8000/docs  账号见下
make open-grafana      # http://localhost:3000       账号见下
make open-prometheus   # http://localhost:9090
```

也可以同时开多个终端分别跑。

**账号密码：**

| 服务 | 地址 | 账号 | 密码 |
|------|------|------|------|
| 后端 API 文档 (Swagger) | http://localhost:8000/docs | `user@example.com` | `string` |
| Grafana | http://localhost:3000 | `admin` | `smart-scheduler-admin` |

> Swagger 页面点右上角绿色锁头 **Authorize** 按钮登录后才能调用需要鉴权的接口。

### 云端 (GKE)

deploy.sh 跑完后脚本直接打印公网 IP，浏览器打开即可。不需要 port-forward。

```bash
# 也可以手动查
kubectl get ingress smart-scheduler-ingress -n smart-scheduler
```

---

## 监控

监控栈在 deploy.sh 结尾自动部署，正常情况不需要单独操作。

**以下情况才需要单独跑：**

```bash
# 改了 helm-prometheus-values.yaml 或 helm-loki-values.yaml 后只更新监控
make monitoring

# 卸载监控（应用不受影响）
make monitoring-down
```

**访问 Grafana：**

```bash
make open-grafana
# http://localhost:3000
# 账号: admin  密码: smart-scheduler-admin
```

**常用 LogQL（在 Grafana → Explore → Loki 里用）：**

```
# 所有 agent 执行日志
{namespace="smart-scheduler", app="backend"} | json | event="agent_exit"

# 执行超过 2 秒的 agent
{namespace="smart-scheduler"} | json | took_ms > 2000

# agent 报错
{namespace="smart-scheduler"} | json | event="agent_error"
```

---

## 日常维护

### K8s 状态管理（`k8s-ops.sh`）

```bash
bash deployment/k8s-ops.sh status      # 查看所有 Pod 状态

bash deployment/k8s-ops.sh stop        # 暂停所有 Pod（数据保留）
bash deployment/k8s-ops.sh start       # 恢复

bash deployment/k8s-ops.sh clean-app   # 删除应用 namespace（⚠️ 数据清空），监控保留
bash deployment/k8s-ops.sh clean-all   # 删除应用 + 监控（⚠️ 全部清空）
```

`clean-app` 之后用 `bash deployment/k8s-deploy.sh` 重新部署。

### Docker Compose 状态管理（`make`）

```bash
make status    # 查看容器状态
make down      # 停止，保留数据
make clean     # 停止，删除数据（⚠️ 数据清空）
```

### 常见问题

**Pod 一直 Pending 或 CrashLoopBackOff**

```bash
kubectl get pods -n smart-scheduler
kubectl describe pod <pod-name> -n smart-scheduler   # 看 Events
kubectl logs <pod-name> -n smart-scheduler           # 看日志
```

**Weaviate 挂了**

```bash
kubectl delete pod -l app=weaviate -n smart-scheduler
# K8s 自动重新拉起
```

**实时看 Pod 状态**

```bash
kubectl get pods -n smart-scheduler -w
```

---

## CI/CD

### CI（自动触发）

push 到 main 或开 PR 时自动跑：

| Workflow | 触发条件 | 做什么 |
|----------|----------|--------|
| `ci-backend.yaml` | BackEnd/ 有改动 | pytest + bandit + pip-audit + Trivy 镜像扫描 |
| `ci-frontend.yaml` | FrontEnd/ 有改动 | lint + build + npm audit + Trivy 镜像扫描 |
| `ci-security.yaml` | 任意改动 | checkov K8s manifest 扫描 |

### CD（手动触发）

GitHub repo → Actions → CD – Deploy → Run workflow → 选环境。

| 环境 | 做什么 | 需要 GCP |
|------|--------|----------|
| staging | build + push 镜像，对集群做 server-side dry-run 校验，不实际部署 | ✅ |
| production | build + push 镜像，apply manifests，等待 rollout 完成 | ✅ |

### GitHub Secrets / Variables 配置

repo Settings → Environments → production（staging 同理）：

**Secrets（加密）**

| 名称 | 内容 |
|------|------|
| `GCP_SA_KEY` | GCP Service Account JSON key（见下方获取方式） |
| `MYSQL_PASSWORD` | 数据库密码 |
| `OPENAI_API_KEY` | OpenAI key |
| `LANGFUSE_PUBLIC_KEY` | Langfuse key |
| `LANGFUSE_SECRET_KEY` | Langfuse key |

**Variables（明文）**

| 名称 | 值 |
|------|------|
| `MYSQL_DATABASE` | `nus_event` |
| `LANGFUSE_BASE_URL` | `https://us.cloud.langfuse.com` |

### 获取 GCP_SA_KEY

```bash
# 创建 Service Account
gcloud iam service-accounts create github-cd \
  --project nus-smart-scheduler

# 授权（推镜像 + 部署到 GKE）
gcloud projects add-iam-policy-binding nus-smart-scheduler \
  --member="serviceAccount:github-cd@nus-smart-scheduler.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding nus-smart-scheduler \
  --member="serviceAccount:github-cd@nus-smart-scheduler.iam.gserviceaccount.com" \
  --role="roles/container.developer"

# 导出 JSON key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-cd@nus-smart-scheduler.iam.gserviceaccount.com

# 把 key.json 内容整个粘贴到 GitHub Secret GCP_SA_KEY，然后删掉本地文件
rm key.json
```

---

## 文件结构说明

```
deployment/
├── k8s-deploy.sh              # 主部署脚本（交互式菜单）
├── k8s-ops.sh                 # 日常维护（stop/start/clean/status）
├── docker-compose.yaml        # 本地开发基础设施
├── docker-compose.dev.yaml    # dev 模式扩展
├── sql/
│   └── nus_event.sql          # 数据库初始化 SQL
└── k8s/
    ├── base/                  # 通用 manifests（所有环境共用）
    │   ├── 00-namespace.yaml
    │   ├── 01-configmap.yaml  # 业务配置（时区、AI 参数、Weaviate 地址）
    │   ├── 10-mysql-pvc.yaml
    │   ├── 11-mysql-deploy.yaml
    │   ├── 12-weaviate-pvc.yaml
    │   ├── 13-weaviate-deploy.yaml
    │   ├── 20-backend-deploy.yaml
    │   ├── 21-frontend-deploy.yaml
    │   ├── 30-ingress.yaml
    │   └── 31-network-policy.yaml
    ├── overlays/
    │   ├── k8s-local/         # 本地差异（storageClass、ingressClass）
    │   └── cloud/             # GKE 差异（pd-balanced、gce ingress、BackendConfig）
    │       ├── kustomization.yaml
    │       └── 32-gce-ingress-resources.yaml
    └── monitoring/
        ├── 00-namespace.yaml
        ├── 10-servicemonitor.yaml
        ├── 20-network-policy.yaml
        ├── helm-prometheus-values.yaml
        └── helm-loki-values.yaml

.github/workflows/
├── ci-backend.yaml
├── ci-frontend.yaml
├── ci-security.yaml
└── cd-deploy.yaml
```

**Secret 不在任何 YAML 文件里。** 本地由 deploy.sh 从 .env 读取后注入；云端 CI/CD 从 GitHub Secrets 注入。

---

## 后端本地测试

```bash
cd BackEnd
source venv/bin/activate
pip install pytest pytest-asyncio pytest-cov httpx
```

**按依赖程度从低到高运行：**

```bash
pytest tests/test_parser.py -v          # 零外部依赖
pytest tests/test_auth.py -v            # 纯函数
pytest tests/test_scheduler.py -v       # 依赖 networkx + ortools
pytest tests/test_api.py -v             # 依赖 TestClient + mock
```

**常用参数：**

```bash
pytest tests/ -x          # 遇到第一个失败立即停止
pytest tests/ -v          # 显示每个测试名称
pytest tests/ -s          # 显示 print() 输出
pytest tests/test_scheduler.py::TestTimeUtils::test_roundtrip   # 跑单个函数
```

**LLM 测试（需要真实 API key，较慢）：**

```bash
pytest tests/llm/test_deepeval.py --override-ini="addopts=" -v -m llm
```

**Langfuse tracing 验证：**

确保 .env 填了 Langfuse key，在 http://localhost:8000/docs 用以下账号测试：

```
username: user@example.com
password: string
```

Swagger 页面点右上角绿色锁头 **Authorize** 登录，调用 `/chat` 接口，Langfuse 后台可看到 trace。