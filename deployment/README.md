# Smart Scheduler – Deployment Guide

## 密钥配置（只需配一次）

    cp .env.example .env
    vi .env    # 填入真实值

.env 是唯一的密钥和环境配置文件。本地、Docker、K8s 全部从它读取。

---

## 环境切换

通过 .env 中的 ENV_MODE 控制部署目标：

| ENV_MODE | 部署方式 | deploy.sh 行为 |
|----------|---------|---------------|
| local  | DB Docker + 本地开发 | 不用 deploy.sh，手动 compose up db |
| docker | Docker Compose 生产  | docker compose up -d --build |
| k3s | 本地 K8s | build → import → kubectl apply |
| cloud | 云端 K8s | 留作将来接入 (EKS/GKE/Helm) |

切换环境只改 ENV_MODE 这一个值，然后跑 bash deployment/deploy.sh。

---

## 1. 本地开发 (ENV_MODE=local)

### 首次进入

    cd deployment && ln -s ../.env .env 
    cd BackEnd && ln -s ../.env .env && source venv/bin/activate
    cd FrontEnd && npm install 


### infra 模式：基础设施在 Docker，业务代码在本地跑

    # 后端（本地热更新）（如果没创建虚拟环境先创建）
    Backend >> uvicorn main:app --reload   # http://localhost:8000

    # 前端（另开终端）
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

## 2. Docker Compose (ENV_MODE=docker)

全部服务打包成镜像运行：

    bash deployment/deploy.sh
    # 或直接: cd deployment && docker compose up --build
    # Frontend: http://localhost  Backend: http://localhost:8000/docs

停止： 

    # 如果去掉 -v 表示保留数据
    cd deployment && docker compose down -v

---

## 3. K8s – k3s (ENV_MODE=k3s)

### 首次安装 k3s

    curl -sfL https://get.k3s.io | sh -
    sudo k3s kubectl get nodes

### 部署

    # .env 里设 ENV_MODE=k3s
    bash deployment/deploy.sh

    # 访问
    sudo k3s kubectl port-forward -n smart-scheduler svc/frontend-svc 8080:80

### 停止 / 再启动

    sudo k3s kubectl delete namespace smart-scheduler
    bash deployment/deploy.sh

### 只更新单个服务

    docker build -t smart_scheduler_backend:latest ./BackEnd
    docker save smart_scheduler_backend:latest | sudo k3s ctr images import -
    sudo k3s kubectl rollout restart deployment/backend -n smart-scheduler

---

## 4. 上云迁移 (ENV_MODE=cloud)

deploy.sh 的 cloud 分支预留了接入口。实际接入时需要：
- .env 加 REGISTRY_URL，配置 kubectl context
- 10-mysql-pvc.yaml 的 storageClassName 改成云厂商的 (如 AWS gp3)
- 或用 Helm chart 统一管理不同环境的差异

---

## 5. K8s 文件说明

    k8s/
    ├── 00-namespace.yaml       # 命名空间
    ├── 01-configmap.yaml       # 非敏感配置
    ├── 10-mysql-pvc.yaml       # MySQL 持久存储
    ├── 11-mysql-deploy.yaml    # MySQL Deployment + Service
    ├── 20-backend-deploy.yaml  # Backend Deployment + Service
    ├── 21-frontend-deploy.yaml # Frontend Deployment + Service
    ├── 30-ingress.yaml         # 路径路由
    └── 31-network-policy.yaml  # 网络策略

Secret 由 deploy.sh 从 .env 动态生成，不存在静态 yaml 文件。

---

## 6. CI/CD (GitHub Actions)

    .github/workflows/
    ├── ci-backend.yaml    # BackEnd/ 改动 → pytest → build image
    ├── ci-frontend.yaml   # FrontEnd/ 改动 → lint → build → build image
    └── cd-deploy.yaml     # 手动触发，staging 只 build，production 推镜像+部署

GitHub repo Settings → Secrets → Actions 中配置：OPENAI_API_KEY
GitHub repo Settings → Variables → Actions 中配置：REGISTRY_URL, REGISTRY_USER（上云时）