# Image Classifier
An end‑to‑end asynchronous image classification pipeline using `Celery` (task queue orchestration), `FastAPI` (for RestAPI), `MinIO` (S3‑compatible, for image storage), and `PostgreSQL` (result persistence), `Prometheus` (for metrics), `webhook` (for notifications).

---

## Folder Structure

```
.
├── api/
│   └── routes.py                  # FastAPI endpoints
├── core/
│   └── classifier.py              # Preprocess + classify logic
├── services/
│   ├── celery_worker.py           # Celery app bootstrap
│   ├── task_handler.py            # Task chain definitions
│   └── storage.py                 # MinIO upload client
├── utils/
│   ├── config.py                  # .env loader & URLs
│   └── logger.py                  # loguru setup
├── docs/ (git ignored internal logs)
│   ├── chunks_head                # Data chunk headers
│   ├── lock                       # Lock files for synchronization
│   └── wal/                       # Write-ahead logging
├── logs/ (git ignored log files)
├── tests/                         # Unit and integration tests
├── imagenet_classes.txt           # 1,000 ImageNet labels
├── main.py                        # FastAPI entrypoint
├── prometheus.yml                 # Prometheus metrics config
├── requirements.txt
├── .env.example                   # .env template
└── README.md
```

---
## Architecture

```text
(Client) ---> FastAPI ─┬─> Celery Task Queue ──┬─> Preprocess
                       │                      ├─> Classify (ResNet18)
                       │                      ├─> Store Result (PostgreSQL)
                       │                      └─> Webhook (Optional POST)
                       └─> /task-status/<id>   ←── Result Polling
                                 ↑
                        Prometheus (metrics)
```

___
## Setup

### Local

```bash
# 1. Clone project
git clone https://github.com/sree-sphere/async-image-classifier.git
cd aync-image-classifier

# 2. Create & edit .env credentials
cp .env.example .env

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up metrics directory for Prometheus multiprocess mode
export PROMETHEUS_MULTIPROC_DIR=/tmp/metrics-multiproc
mkdir -p $PROMETHEUS_MULTIPROC_DIR
rm -f $PROMETHEUS_MULTIPROC_DIR/*

# 5. Start services
# FastAPI app:
uvicorn main:app --reload
# Celery worker:
celery -A services.celery_worker.celery_app worker --loglevel=info
# Prometheus (optional):
prometheus --config.file=./prometheus.yml
# Celery Flower (optional):
celery -A services.celery_worker.celery_app flower --port=5555
```

### Docker

```bash
# 1. Copy & configure .env for Docker
cp .env.example .env

# 2. Start all services (RabbitMQ, Redis, MinIO, Postgres, Worker, RESTAPI)
docker-compose up --build
```
___

# Usage notes

Visit [webhook.site](https://webhook.site/) for webhook notifications and URL

Ensure local services running:
 - Default: Redis on localhost:6379 or RabbitMQ on localhost:5672
 - Uvicorn on localhost:8000
 - MinIO on localhost:9000
 - PostgreSQL on localhost:5432
 - Prometheus (optional) on localhost:9090
 - Celery Flower (optional) on localhost:5555

 ___
 # Monitoring (Prometheus + Grafana)

## Metrics

`GET http://localhost:8000/metrics/`

Queries includes:

- image_task_success_total
- image_task_failure_total
- image_task_latency_seconds
- webhook_success_total
- webhook_failure_total
- webhook_latency_seconds
- celery_queue_depth

Example: `curl -s http://localhost:8000/metrics | grep 'image_task_success_total'`

Note: For docker use the container name `- targets: ['api:8000']`