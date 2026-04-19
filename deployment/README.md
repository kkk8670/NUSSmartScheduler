# Smart Scheduler – Deployment Guide

## 整体流程

```
首次准备（每台机器只做一次）
│
├── 1. 装 helm
│      curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
│      helm version   # 验证安装成功
│
├── 2. 准备 K8s 环境
│      Mac：Docker Desktop → Settings → Kubernetes → Enable → Apply & Restart
│           等左下角状态变绿（约 1-2 分钟）
│      Linux：curl -sfL https://get.k3s.io | sh -
│
└── 3. 配置 .env
       cp .env.example .env
       # 必填：MYSQL_PASSWORD / MYSQL_DATABASE / OPENAI_API_KEY / DB_URL
       # 可选：LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY（不填则 tracing 禁用）


每次部署 / 更新代码或 yaml（一条命令搞定）
│
└── bash deployment/deploy.sh
       │
       ├── [1] docker build backend + frontend 镜像
       ├── [2] Linux: k3s ctr images import / Mac: 直接用（共享 daemon）
       ├── [3] kubectl apply -k overlays/k8s-local     ← kustomize，幂等
       ├── [4] kubectl create secret app-secret        ← 注入密钥，幂等
       ├── [5] kubectl rollout status（等 backend/frontend/mysql 就绪）
       └── [6] deploy_monitoring()
              ├── kubectl apply namespace + network-policy
              ├── helm upgrade --install kube-prom     ← Prometheus + Grafana
              ├── helm upgrade --install loki          ← Loki + Promtail
              │   （--wait，等所有监控 pod 就绪）
              └── kubectl apply servicemonitor         ← CRD 此时已就绪


只更新监控配置（改了 helm-*-values.yaml，不重新 build 镜像）
│
└── make monitoring                                    ← 只跑 helm upgrade，秒级


日常操作
│
├── 查看状态        bash deployment/ops.sh status
├── 暂停（保数据）   bash deployment/ops.sh stop
├── 恢复            bash deployment/ops.sh start
├── 看 Grafana      make grafana  →  http://localhost:3000
└── 看 Prometheus   kubectl port-forward -n monitoring \
                      svc/kube-prom-kube-prometheus-prometheus 9090:9090
                      
# 这里grafana的用户名和密码：
admin / smart-scheduler-admin

停止与清理
│
├── 暂停所有 Pod，数据保留，下次 start 恢复
│      bash deployment/ops.sh stop
│
├── 删除应用，监控保留（重新 deploy.sh 可恢复，但数据库清空）
│      bash deployment/ops.sh clean-app
│
└── 完全清除，从零开始
       bash deployment/ops.sh clean-all
```


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

## 7. 本地测试（后端）
```
BackEnd/
├── tests/
│   ├── conftest.py
│   ├── test_scheduler.py
│   ├── test_auth.py
│   ├── test_api.py
│   └── test_parser.py
├── requirements.txt
└── main.py
```

安装测试依赖`pip install pytest pytest-asyncio httpx`

本地测试方法
```
# 只跑某一个文件
pytest tests/test_parser.py

# 只跑某一个 class
pytest tests/test_scheduler.py::TestTimeUtils

# 只跑某一个函数
pytest tests/test_scheduler.py::TestTimeUtils::test_roundtrip

# 跑失败时立刻停下来，不继续跑后面的
pytest tests/ -x

# 显示每个测试的名字和结果（默认只显示点）
pytest tests/ -v

# 显示 print() 的输出（默认被 pytest 吞掉）
pytest tests/ -s
```

建议步骤：
```
# 1：零依赖 
pytest tests/test_parser.py -v

# 2：纯函数，但依赖 constants 配置
pytest tests/test_auth.py -v

# 3：不依赖 DB 和 LLM，只用 MagicMock
pytest tests/test_react_trace.py -v 

# 4：依赖 networkx 和 ortools
pytest tests/test_scheduler.py -v

# 5：依赖 TestClient 和 mock， 
pytest tests/test_api.py -v
```

## 8. langfuse

- 第一步要注册langfuse，拿到api key。（在`.env`中填入）

- 其次需要测试一下运行，直接后台`http://localhost:8000/docs`运行。测试账户：
```
{
  "username": "user@example.com",
  "password": "string"
}
# id: 3
```
Swagger 页面最上方，点击绿色的小锁 Authorize 按钮，填入`username`和`password`登录。

- 然后在`/chat`处填入prompt运行。


## 9. k8s monitoring

架构
```
monitoring namespace (Helm 管理)          s
mart-scheduler namespace (kustomize 管理)
┌──────────────────────────────┐          ┌──────────────────────────────┐
│  Prometheus                  │◄─scrape──│  backend /metrics            │
│  Grafana                     │          │  (prometheus-fastapi-        │
│  Loki                        │◄─push────│   instrumentator)            │
│  Promtail (DaemonSet)        │  logs    │                              │
└──────────────────────────────┘          └──────────────────────────────┘

两个 namespace 通过 NetworkPolicy（monitoring/20-network-policy.yaml）打通，
其余流量仍被 default-deny 隔离。
```

文件说明
```
deployment/k8s/monitoring/
├── 00-namespace.yaml            # monitoring namespace（带自定义 label）
├── 10-servicemonitor.yaml       # 告诉 Prometheus 去哪里 scrape backend
├── 20-network-policy.yaml       # 开放 Prometheus→backend:8000 的流量通道
├── helm-prometheus-values.yaml  # kube-prometheus-stack 裁剪配置
└── helm-loki-values.yaml        # loki-stack 配置（含 Promtail pipeline）
```

- 前提条件 安装helm（只做一次，如果没安装）：
`curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash`

- 下面两种可选部署

    A. 随应用一起部署
    `bash deployment/deploy.sh`
    应用和监控一起装，适合第一次搭环境或者应用有更新的时候。

    B. 只更新监控
    `make monitoring`
    应用不动，只重新装/更新 Prometheus + Grafana + Loki。适合改了 helm-prometheus-values.yaml 或 helm-loki-values.yaml 之后单独生效。

- 部署完k8s之后的使用操作，可随意操作

    - 访问 Grafana（部署完随时可以跑）
    ```
    make grafana
    # 然后打开 http://localhost:3000
    # 账号: admin  密码: smart-scheduler-admin
    ```

    - 卸载监控栈
    ```
    make monitoring-down
    # 应用（smart-scheduler namespace）完全不受影响
    ```

使用监控：

Grafana 开箱即有两个 datasource：
- Prometheus：HTTP 请求数、延迟（P95/P99）、错误率、节点资源
- Loki：结构化日志，可用 LogQL 查询 backend 的 jlog() 输出

常用 LogQL 示例：
```
# 查看所有 agent 执行日志
{namespace="smart-scheduler", app="backend"} | json | event="agent_exit"

# 查看执行超过 2 秒的 agent
{namespace="smart-scheduler"} | json | took_ms > 2000

# 查看 ReAct 错误
{namespace="smart-scheduler"} | json | event="agent_error"
```
