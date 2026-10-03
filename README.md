<div align="center">

# KaaS — Kubernetes as a Service

**A small REST API that turns one HTTP request into a running app on Kubernetes.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white)
![Helm](https://img.shields.io/badge/Helm-0F1689?logo=helm&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-F46800?logo=grafana&logoColor=white)

<img width="2560" height="1400" alt="architecture" src="https://github.com/user-attachments/assets/f707c160-6a9a-4a2d-be47-4d4bf983e244" />


</div>

## About

KaaS lets you deploy applications to a Kubernetes cluster without writing any YAML. You send the image name, the number of replicas and a port, and KaaS creates everything the app needs to run. It can also set up a PostgreSQL database for you, report the status of your deployments, and export metrics for monitoring.

## Features

- **Deploy an app in one request** — creates the Deployment and Service, plus an Ingress and Secret if you want them
- **PostgreSQL on demand** — provisions a database and returns its credentials
- **Deployment status** — see replicas and pods for one app or all of them
- **Monitoring included** — Prometheus metrics with a ready-to-run Prometheus + Grafana setup
- **Interactive API docs** — Swagger UI and ReDoc, served locally so they work offline
- **Helm chart** — to install KaaS itself on a cluster

## Getting started

You need Python 3.12+ and access to a Kubernetes cluster (minikube or kind is fine) with a kubeconfig at `~/.kube/config`.

```bash
git clone https://github.com/pooyatfn/KaaS.git
cd KaaS
pip install -r requirements.txt
fastapi run main.py --port 8000
```

Then open <http://localhost:8000/docs>.

Prefer Docker? Run `docker compose up --build` instead.

## API

<img width="2400" height="1842" alt="swagger-ui" src="https://github.com/user-attachments/assets/8a971962-37b8-428a-acc8-b1174e8c3b0d" />


| Method | Path | What it does |
| --- | --- | --- |
| `POST` | `/service1/` | Deploy an application |
| `GET` | `/service2/` | Get the status of one deployment |
| `GET` | `/service3/` | Get the status of all deployments |
| `POST` | `/postgres/` | Create a PostgreSQL database |
| `GET` | `/healthz/` | Health check |

Full details for every endpoint are in the interactive docs at `/docs`.

### Example

Deploy two replicas of NGINX:

```bash
curl -X POST "http://localhost:8000/service1/?app_name=web&replicas=2&image_address=nginx&image_tag=latest&domain_address=web&service_port=80" \
  -H "Content-Type: application/json" \
  -d '{"resources": {"cpu": "250m", "memory": "128Mi"}, "envs": {}}'
```

Check on it:

```bash
curl "http://localhost:8000/service2/?deployment_name=web-deployment"
```

## Monitoring

KaaS exports request, failure and response-time metrics on port `8001`. To start Prometheus and Grafana:

```bash
docker compose -f docker-compose.monitoring.yml up -d
```

- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000> (login `grafana` / `grafana`)

## Deploy with Helm

```bash
docker build -t localhost:5000/api:latest .
docker push localhost:5000/api:latest
helm install kaas-api ./kaas-api
```

## Project structure

```text
KaaS/
├── main.py                        # API routes
├── k8s_utils.py                   # Kubernetes logic
├── metrics.py                     # Prometheus metrics
├── Dockerfile
├── docker-compose.yml             # Runs the API
├── docker-compose.monitoring.yml  # Prometheus + Grafana
├── prometheus/                    # Prometheus config
├── kaas-api/                      # Helm chart
└── static/                        # Swagger UI and ReDoc assets
```
