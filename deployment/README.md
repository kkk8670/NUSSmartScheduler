# Smart Scheduler – Deployment Guide

## 密钥配置（只需配一次）

    cp .env.example .env
    vi .env    # 填入真实值

.env 是唯一的密钥和环境配置文件。本地、Docker、K8s 全部从它读取。

---

## 环境切换

### 本地开发：

使用 `docker` 命令或 `makefile` 命令


makefile 命令见下表：
| 命令 | 场景 | 访问地址 |
|------|------|----------|
| `make infra` | 只起 DB + Weaviate，后端/前端本地跑 | Frontend: http://localhost:5173 · Backend: http://localhost:8000 |
| `make dev` | DB + Weaviate + Backend 进 Docker（热更新），前端本地跑 | Frontend: http://localhost:5173 · Backend: http://localhost:8000 |
| `make prod` | 全部进 Docker，生产构建 | Frontend: **http://localhost** · Backend: http://localhost:8000/docs |
| `make down` | 停所有容器 | — |
| `make clean` | 停容器并删数据卷（⚠️ 数据清空） | — |
| `make status` | 查看容器状态 | — |


### K8s 部署 ：

通过 .env 中的 ENV_MODE 控制部署目标：

| ENV_MODE | 部署方式 | deploy.sh 行为 |
|----------|---------|---------------|
| `k3s`    | 本地 K8s (k3s)        | build → import → kubectl apply (k3s overlay) |
| `cloud`  | 云端 K8s              | 预留接入口，见下文                      |

切换云环境只改 ENV_MODE ，然后跑 bash deployment/deploy.sh。

**K8s 环境参数**（storageClass / ingressClass / domain）集中维护在：

    deployment/k8s/env-config.yaml

新增云厂商或修改参数值，只改这一个文件（以及对应 overlay 的 kustomization.yaml）。

---

## 1. 本地开发

### 首次进入

    cd deployment && ln -s ../.env .env 
    cd BackEnd && ln -s ../.env .env && source venv/bin/activate
    cd FrontEnd && npm install 


### infra 模式：基础设施在 Docker，业务代码在本地跑

    # 后端（本地热更新）（如果没创建虚拟环境先创建）
    Backend >> uvicorn main:app --reload   # http://localhost:8000

    # 前端（另开终端） ❗️注意端口是5173
    FrontEnd >> npm run dev   # http://localhost:5173

    # 基础设施（另开终端）
    deployment >> docker compose up db weaviate -d
    # 或者
    root >> make infra

 
### dev 模式：infra + 后端在docker

    cd deployment && docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up
    # 或者
    # root >> make dev

    # 前端仍在本地: FrontEnd >> npm run dev


### 停止：

    # 保留数据
    deployment >> docker compose down     
    # 或者
    make down 

    # 删除数据
    deployment >> docker compose down -v   
    # 或者
    make clean


    # Ctrl+C 停本地的 uvicorn / npm

---

## 2. Docker Compose

全部服务打包成镜像运行：

    bash deployment/deploy.sh
    # 或直接: cd deployment && docker compose up --build
    # Frontend: http://localhost  # ❗️注意端口是80
    # Backend: http://localhost:8000/docs

停止： 

    # 如果去掉 -v 表示保留数据
    cd deployment && docker compose down -v

---

## 3. K8s – 单机模拟 (ENV_MODE=k8s-local)

### Linux (k3s)

首次安装 k3s：

    curl -sfL https://get.k3s.io | sh -
    sudo k3s kubectl get nodes

部署：

    # .env 里设 ENV_MODE=k8s-local
    bash deployment/deploy.sh

访问：

    sudo k3s kubectl port-forward -n smart-scheduler svc/frontend-svc 8080:80

停止 / 重部署：

    sudo k3s kubectl delete namespace smart-scheduler
    bash deployment/deploy.sh

只更新单个服务：

    docker build -t smart_scheduler_backend:latest ./BackEnd
    docker save smart_scheduler_backend:latest | sudo k3s ctr images import -
    sudo k3s kubectl rollout restart deployment/backend -n smart-scheduler

---

### Mac / Windows (Docker Desktop)

首次启动 Kubernetes：
Docker Desktop → Settings → Kubernetes → ✅ Enable Kubernetes → Apply & Restart，等状态栏变绿。

Mac/Win 需手动安装 Ingress Controller（只需一次）：

    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.1/deploy/static/provider/cloud/deploy.yaml

部署：

    # .env 里设 ENV_MODE=k8s-local
    bash deployment/deploy.sh

访问：

    kubectl port-forward -n smart-scheduler svc/frontend-svc 8080:80
    # 保持窗口打开，访问：http://localhost:8080

停止 / 重部署：

    kubectl delete namespace smart-scheduler
    bash deployment/deploy.sh

只更新单个服务：

    # 以后端为例
    docker build -t smart_scheduler_backend:latest ./BackEnd
    kubectl rollout restart deployment/backend -n smart-scheduler
    # Docker Desktop 共享 daemon，无需手动 import 镜像

> **Windows 说明**：请使用 Git Bash 运行 `deploy.sh`。WSL 用户的 `uname -s` 返回 Linux，deploy.sh 会走 k3s 分支，请在 WSL 内安装 k3s 或切换到 Git Bash。

---

## 4. 上云迁移 (ENV_MODE=cloud)

1. 修改 `deployment/k8s/env-config.yaml` → `envs.cloud` 下填入真实 domain、imageRegistry
2. 修改 `deployment/k8s/overlays/cloud/kustomization.yaml` 中对应 patch 值
3. 确认本地 kubectl context 已切换到云端集群（`kubectl config current-context`）
4. 取消 `deploy.sh` cloud 分支中的注释，启用 push + apply 步骤

---

## 5. K8s 文件说明

    deployment/k8s/
    ├── env-config.yaml          # 环境参数字典（storageClass / ingressClass / domain）
    ├── base/                    # 通用 manifests（不含环境差异）
    │   ├── kustomization.yaml
    │   ├── 00-namespace.yaml
    │   ├── 01-configmap.yaml
    │   ├── 10-mysql-pvc.yaml
    │   ├── 11-mysql-deploy.yaml
    │   ├── 12-weaviate-pvc.yaml
    │   ├── 13-weaviate-deploy.yaml
    │   ├── 20-backend-deploy.yaml
    │   ├── 21-frontend-deploy.yaml
    │   ├── 30-ingress.yaml
    │   └── 31-network-policy.yaml
    └── overlays/
        ├── k3s/
        │   └── kustomization.yaml    # storageClass=local-path, ingress=traefik
        └── cloud/
            └── kustomization.yaml    # storageClass=gp3, ingress=nginx

Secret 由 `deploy.sh` 从 `.env` 动态生成，不存在静态 yaml 文件。

---

## 6. CI/CD (GitHub Actions)

    .github/workflows/
    ├── ci-backend.yaml    # BackEnd/ 改动 → pytest → build image
    ├── ci-frontend.yaml   # FrontEnd/ 改动 → lint → build → build image
    └── cd-deploy.yaml     # 手动触发，staging 只 build，production 推镜像+部署

GitHub repo Settings → Secrets → Actions 中配置：OPENAI_API_KEY
GitHub repo Settings（上云时） → Variables → Actions 中配置：REGISTRY_URL, REGISTRY_USER 