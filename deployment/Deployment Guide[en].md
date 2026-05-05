# Smart Scheduler — Deployment Guide

## Table of Contents

- [Overall Architecture](#overall-architecture)
- [Prerequisites](#prerequisites)
- [Daily Development (Local)](#daily-development-local)
- [K8s Local Deployment](#k8s-local-deployment)
- [K8s Cloud Deployment (GKE)](#k8s-cloud-deployment-gke)
- [Accessing Services](#accessing-services)
- [Monitoring](#monitoring)
- [Routine Maintenance](#routine-maintenance)
- [CI/CD](#cicd)
- [File Structure](#file-structure)
- [Backend Local Testing](#backend-local-testing)

---

## Overall Architecture

```
Local Dev                K8s Local             K8s Cloud (GKE)
─────────────            ──────────────        ──────────────────────
make infra/dev      →    bash deploy.sh   →    bash deploy.sh
Docker Compose           Docker Desktop         GKE asia-southeast1
                         or k3s (Linux)         scheduler-cluster
```

All three modes start from the same codebase. `deploy.sh` uses an interactive menu to select the target environment.

---

## Prerequisites

**Run once per machine.**

### 1. Core Tools

```bash
# Helm (required for K8s monitoring stack)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

### 2. K8s Environment (Local)

**Mac / Windows**
Docker Desktop → Settings → Kubernetes → ✅ Enable Kubernetes → Apply & Restart
Wait for the status indicator in the bottom-left to turn green (approximately 1–2 minutes).

**Linux**
```bash
curl -sfL https://get.k3s.io | sh -
sudo k3s kubectl get nodes   # verify
```

### 3. Configure .env

```bash
cp .env.example .env
```

Required fields:

| Field | Description |
|-------|-------------|
| `MYSQL_PASSWORD` | Database password, set your own |
| `MYSQL_DATABASE` | Fixed value: `nus_event` |
| `OPENAI_API_KEY` | OpenAI key |

Optional fields (features are disabled if left blank):

| Field | Description |
|-------|-------------|
| `LANGFUSE_PUBLIC_KEY` | Langfuse tracing |
| `LANGFUSE_SECRET_KEY` | Langfuse tracing |
| `GRAFANA_SMTP_USER` | Email alerts |
| `GRAFANA_SMTP_PASSWORD` | Email alerts |

---

## Daily Development (Local)

Local development does not use K8s. Docker Compose brings up the infrastructure while code runs on the host machine with hot-reload.

### First-Time Setup

```bash
cd deployment && ln -s ../.env .env      # symlink .env for Compose

cd BackEnd
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cd FrontEnd && npm install
```

### Starting Up

**Mode 1: Start only the database + Weaviate; run all code locally (most common)**

```bash
make infra

# Terminal 1 — Backend
cd BackEnd && uvicorn main:app --reload
# Access: http://localhost:8000/docs

# Terminal 2 — Frontend
cd FrontEnd && npm run dev
# Access: http://localhost:5173
```

**Mode 2: Backend in Docker (with hot-reload), frontend runs locally**

```bash
make dev
cd FrontEnd && npm run dev   # frontend still local at http://localhost:5173
```

**Mode 3: Everything packaged as images**

```bash
make prod
# Frontend: http://localhost
# Backend:  http://localhost:8000/docs
```

### Stopping

```bash
make down      # stop containers, keep data
make clean     # stop containers, delete volumes (⚠️ data will be erased)
```

---

## K8s Local Deployment

Used to validate K8s configuration — behavior is identical to the cloud environment.

```bash
bash deployment/k8s-deploy.sh
# Select 1 (local) from the menu
```

`deploy.sh` automatically performs the following steps and **finishes once all Pods reach Running status**:

```
Build images
  → Import into cluster
    → kubectl apply manifests (create namespace, Pods, Services, NetworkPolicy)
      → kubectl create secret (inject DB password, API keys)
        → Wait for all Pods to reach Running
          → Deploy monitoring stack (Prometheus + Grafana + Loki)
            → Done ✅
```

**Deploy finishing does not mean the service is accessible.** K8s Pods run inside the cluster's internal network and are not reachable from outside — similar to a process running on a server behind a closed firewall. The `make open-*` commands (see [Accessing Services](#accessing-services) below) open a temporary tunnel that maps cluster ports to localhost. Cloud deployments use Ingress and a public IP, so this step is not needed there.

**Redeploy** (when code has been updated):

```bash
bash deployment/k8s-deploy.sh   # Select 1 again — idempotent, will overwrite
```

**Update a single service** (without rebuilding all images):

```bash
# Example: backend
docker build -t smart_scheduler_backend:1.0.0 ./BackEnd

# Mac (Docker Desktop shares the daemon — no import needed)
kubectl rollout restart deployment/backend -n smart-scheduler

# Linux (k3s)
docker save smart_scheduler_backend:1.0.0 | sudo k3s ctr images import -
sudo k3s kubectl rollout restart deployment/backend -n smart-scheduler
```

---

## K8s Cloud Deployment (GKE)

### One-Time Setup

**1. Install gcloud CLI**
https://cloud.google.com/sdk/docs/install

**2. Log in and create the cluster**

```bash
gcloud auth login
gcloud config set project nus-smart-scheduler

gcloud container clusters create scheduler-cluster \
  --region asia-southeast1 \
  --machine-type e2-medium \
  --num-nodes 2

# Fetch cluster credentials to local (writes to ~/.kube/config so kubectl works)
gcloud container clusters get-credentials scheduler-cluster \
  --region asia-southeast1 \
  --project nus-smart-scheduler
```

**3. Create an Artifact Registry repository**

```bash
gcloud artifacts repositories create smart-scheduler \
  --repository-format=docker \
  --location=asia-southeast1
```

**4. Onboarding additional team members**

After being added to the GCP project IAM, each member runs once:

```bash
gcloud auth login
gcloud container clusters get-credentials scheduler-cluster \
  --region asia-southeast1 --project nus-smart-scheduler
```

### Deploying

```bash
bash deployment/k8s-deploy.sh
# Select 2 (cloud HTTP) or 3 (cloud HTTPS) from the menu
```

**Option 2 — HTTP (recommended to start with)**
No domain required. GKE automatically assigns a public IP; the script prints the access URL when done.

**Option 3 — HTTPS**
Requires a domain and a static IP. The script will prompt interactively:
```
Domain (e.g. scheduler.example.com): your.domain.com
Static IP name (from: gcloud compute addresses list): scheduler-static-ip
```
The certificate is issued automatically by GCP. Initial provisioning takes 10–60 minutes; HTTPS certificate errors during this period are expected.

After a cloud deployment, access the service via the public IP directly — **no port-forwarding needed**.

---

## Accessing Services

### Local K8s

After `deploy.sh` completes, run the following commands in new terminals and **keep those terminal windows open** (closing them drops the tunnel):

```bash
make open-frontend     # http://localhost:8080
make open-backend      # http://localhost:8000/docs  (see credentials below)
make open-grafana      # http://localhost:3000       (see credentials below)
make open-prometheus   # http://localhost:9090
```

You can open multiple terminals and run each command in parallel.

**Credentials:**

| Service | URL | Username | Password |
|---------|-----|----------|----------|
| Backend API docs (Swagger) | http://localhost:8000/docs | `user@example.com` | `string` |
| Grafana | http://localhost:3000 | `admin` | `smart-scheduler-admin` |

> On the Swagger page, click the green lock icon **Authorize** in the top-right corner before calling any authenticated endpoints.

### Cloud (GKE)

The script prints the public IP upon completion. Open it in a browser. No port-forwarding required.

```bash
# Can also check manually
kubectl get ingress smart-scheduler-ingress -n smart-scheduler
```

---

## Monitoring

The monitoring stack is deployed automatically at the end of `deploy.sh`. No manual action is needed under normal circumstances.

**Only run the following when needed:**

```bash
# After modifying helm-prometheus-values.yaml or helm-loki-values.yaml
make monitoring

# Uninstall monitoring (application is unaffected)
make monitoring-down
```

**Accessing Grafana:**

```bash
make open-grafana
# http://localhost:3000
# Username: admin  Password: smart-scheduler-admin
```

**Common LogQL queries (use in Grafana → Explore → Loki):**

```
# All agent execution logs
{namespace="smart-scheduler", app="backend"} | json | event="agent_exit"

# Agents that took over 2 seconds
{namespace="smart-scheduler"} | json | took_ms > 2000

# Agent errors
{namespace="smart-scheduler"} | json | event="agent_error"
```

---

## Routine Maintenance

### K8s State Management (`k8s-ops.sh`)

```bash
bash deployment/k8s-ops.sh status      # view all Pod statuses

bash deployment/k8s-ops.sh stop        # suspend all Pods (data retained)
bash deployment/k8s-ops.sh start       # resume

bash deployment/k8s-ops.sh clean-app   # delete application namespace (⚠️ data erased), monitoring kept
bash deployment/k8s-ops.sh clean-all   # delete application + monitoring (⚠️ everything erased)
```

After `clean-app`, redeploy with `bash deployment/k8s-deploy.sh`.

### Docker Compose State Management (`make`)

```bash
make status    # view container status
make down      # stop, keep data
make clean     # stop, delete data (⚠️ data erased)
```

### Troubleshooting

**Pod stuck in Pending or CrashLoopBackOff**

```bash
kubectl get pods -n smart-scheduler
kubectl describe pod <pod-name> -n smart-scheduler   # check Events
kubectl logs <pod-name> -n smart-scheduler           # check logs
```

**Weaviate crashed**

```bash
kubectl delete pod -l app=weaviate -n smart-scheduler
# K8s will automatically restart it
```

**Watch Pod status in real time**

```bash
kubectl get pods -n smart-scheduler -w
```

---

## CI/CD

### CI (Automatically Triggered)

Runs automatically on push to `main` or when a PR is opened:

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `ci-backend.yaml` | Changes in `BackEnd/` | pytest + bandit + pip-audit + Trivy image scan |
| `ci-frontend.yaml` | Changes in `FrontEnd/` | lint + build + npm audit + Trivy image scan |
| `ci-security.yaml` | Any change | checkov K8s manifest scan |

### CD (Manually Triggered)

GitHub repo → Actions → CD – Deploy → Run workflow → Select environment.

| Environment | What it does | Requires GCP |
|-------------|--------------|--------------|
| staging | Build + push images, run server-side dry-run validation against cluster, no actual deployment | ✅ |
| production | Build + push images, apply manifests, wait for rollout to complete | ✅ |

### GitHub Secrets / Variables Setup

Go to repo Settings → Environments → production (same for staging):

**Secrets (encrypted)**

| Name | Value |
|------|-------|
| `GCP_SA_KEY` | GCP Service Account JSON key (see below) |
| `MYSQL_PASSWORD` | Database password |
| `OPENAI_API_KEY` | OpenAI key |
| `LANGFUSE_PUBLIC_KEY` | Langfuse key |
| `LANGFUSE_SECRET_KEY` | Langfuse key |

**Variables (plaintext)**

| Name | Value |
|------|-------|
| `MYSQL_DATABASE` | `nus_event` |
| `LANGFUSE_BASE_URL` | `https://us.cloud.langfuse.com` |

### Obtaining GCP_SA_KEY

```bash
# Create a Service Account
gcloud iam service-accounts create github-cd \
  --project nus-smart-scheduler

# Grant permissions (push images + deploy to GKE)
gcloud projects add-iam-policy-binding nus-smart-scheduler \
  --member="serviceAccount:github-cd@nus-smart-scheduler.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding nus-smart-scheduler \
  --member="serviceAccount:github-cd@nus-smart-scheduler.iam.gserviceaccount.com" \
  --role="roles/container.developer"

# Export JSON key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-cd@nus-smart-scheduler.iam.gserviceaccount.com

# Paste the entire contents of key.json into GitHub Secret GCP_SA_KEY, then delete the local file
rm key.json
```

---

## File Structure

```
deployment/
├── k8s-deploy.sh              # Main deployment script (interactive menu)
├── k8s-ops.sh                 # Routine maintenance (stop/start/clean/status)
├── docker-compose.yaml        # Local development infrastructure
├── docker-compose.dev.yaml    # Dev mode extension
├── sql/
│   └── nus_event.sql          # Database initialization SQL
└── k8s/
    ├── base/                  # Common manifests (shared across all environments)
    │   ├── 00-namespace.yaml
    │   ├── 01-configmap.yaml  # App config (timezone, AI params, Weaviate address)
    │   ├── 10-mysql-pvc.yaml
    │   ├── 11-mysql-deploy.yaml
    │   ├── 12-weaviate-pvc.yaml
    │   ├── 13-weaviate-deploy.yaml
    │   ├── 20-backend-deploy.yaml
    │   ├── 21-frontend-deploy.yaml
    │   ├── 30-ingress.yaml
    │   └── 31-network-policy.yaml
    ├── overlays/
    │   ├── k8s-local/         # Local overrides (storageClass, ingressClass)
    │   └── cloud/             # GKE overrides (pd-balanced, gce ingress, BackendConfig)
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

**Secrets are not stored in any YAML file.** Locally, `deploy.sh` reads them from `.env` and injects them at runtime. In cloud CI/CD, they are injected from GitHub Secrets.

---

## Backend Local Testing

```bash
cd BackEnd
source venv/bin/activate
pip install pytest pytest-asyncio pytest-cov httpx
```

**Run tests in order of increasing dependencies:**

```bash
pytest tests/test_parser.py -v          # no external dependencies
pytest tests/test_auth.py -v            # pure functions
pytest tests/test_scheduler.py -v       # requires networkx + ortools
pytest tests/test_api.py -v             # requires TestClient + mock
```

**Common flags:**

```bash
pytest tests/ -x          # stop immediately on first failure
pytest tests/ -v          # show each test name
pytest tests/ -s          # show print() output
pytest tests/test_scheduler.py::TestTimeUtils::test_roundtrip   # run a single function
```

**LLM tests (requires a real API key, runs slowly):**

```bash
pytest tests/llm/test_deepeval.py --override-ini="addopts=" -v -m llm
```

**Verifying Langfuse tracing:**

Make sure the Langfuse keys are set in `.env`, then test via http://localhost:8000/docs using these credentials:

```
username: user@example.com
password: string
```

On the Swagger page, click the green lock icon **Authorize** in the top-right corner to log in, then call the `/chat` endpoint. The trace should appear in the Langfuse dashboard.