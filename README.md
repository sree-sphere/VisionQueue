## Status

| Type      | Badge |
|-----------|-------|
| Tests     | [![Tests](https://img.shields.io/github/actions/workflow/status/sree-sphere/async-image-classifier/tests.yml?branch=main&label=tests&logo=github)](https://github.com/sree-sphere/async-image-classifier/actions/workflows/tests.yml) |
| Coverage  | [![Coverage](https://img.shields.io/coveralls/github/sree-sphere/async-image-classifier/main?style=flat-square&logo=coveralls&color=brightgreen)](https://coveralls.io/github/sree-sphere/async-image-classifier?branch=main) |


# Image Classification

This system provides scalable, end-to-end image classification with through distributed task queues, object storage, and comprehensive monitoring.

## Features

- *Asynchronous Processing*: Non-blocking image classification using Celery task queues
- *RESTful API*: FastAPI-powered endpoints for image submission and result retrieval
- *Scalable Storage*: MinIO S3-compatible object storage for image persistence
- *Result Persistence*: PostgreSQL database for classification results and metadata
- *Comprehensive Monitoring*: Prometheus metrics with Grafana dashboards
- *Webhook Notifications*: Configurable POST notifications for task completion
- *Production Ready*: Docker containerization with health checks and service dependencies

---
## Architecture

```text
(Client) ---> FastAPI ─┬─> Upload Image ─────> MinIO (Store image)
                       │
                       ├─> Celery Task Queue ─┬─> Preprocess Image
                       │                      ├─> Classify (ResNet18)
                       │                      ├─> Store Result (PostgreSQL)
                       │                      └─> Webhook (Optional POST)
                       │
                       └─> /task-status/<id>  ←── Result Polling
                                 ↑
                        Prometheus (metrics)
                                 ↑
         ┌────────────────────┬──┴──────────────┐
         │                    │                 │
     Prometheus          Grafana Dashboards   Celery Flower
  (collect metrics)     (visualize metrics)   (monitor tasks)

```

___
## Setup

```
# Clone repo
git clone https://github.com/sree-sphere/VisionQueue.git
cd VisionQueue

# Configure .env variables. Edit as needed.
cp .env.example .env
```

See [.env.example](.env.example) for required environment variables.

### Local

```bash
# Install dependencies
pip install -r requirements.txt

# Set up Prometheus metrics directory
mkdir -p /tmp/metrics-multiproc
export PROMETHEUS_MULTIPROC_DIR=/tmp/metrics-multiproc

# Start services individually
# 1. FastAPI application
uvicorn main:app --reload

# 2. Celery worker (separate terminal)
celery -A services.celery_worker.celery_app worker --loglevel=info

# 3. Optional: Celery Flower monitoring
celery -A services.celery_worker.celery_app flower --port=5555

# 4. Optional: Prometheus metrics
prometheus --config.file=./prometheus.yml
```

### Docker

```bash
# Start all services
docker-compose up --build
```

---
## Folder Structure

```
.
├── .github/
│   └── workflows/
│       └── tests.yml              # GitHub Actions CI
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
├── grafana/                       # Grafana dashboard config
│   ├── dashboards/                # Custom dashboard exports for Celery worker metrics
│   └── provisioning/
│       ├── dashboards/            # Maps custom files into Grafana UI automatically on container startup
│       └── datasources/           # Defines Prometheus as data source
├── logs/ (git ignored log files)

├── tests/                         # Unit and integration tests
├── imagenet_classes.txt           # 1,000 ImageNet labels
├── main.py                        # FastAPI entrypoint
├── Makefile                       # Automation for tests and Docker build
├── prometheus.yml                 # Prometheus metrics config
├── docker-compose.yml             # Multi-container deployment
├── Dockerfile                     # Container build instructions
├── requirements.txt
├── .env.example                   # .env template
└── README.md
```

___

# Usage notes

Visit [webhook.site](https://webhook.site/) for webhook id and viewing notifications.

Ensure local services running:
 - Default: Redis [localhost:6379](localhost:6379) or RabbitMQ [localhost:5672](localhost:5672)
 - FastAPI (Uvicorn) on [localhost:8000/docs](localhost:8000/docs) for image upload & classification (Main application)
 - MinIO on [localhost:9000](localhost:9000) to store uploaded images for classification.
 - PostgreSQL on [localhost:5432](localhost:5432) to store classification results and metadata.

 - Prometheus (optional) on:
    - [localhost:9090/graph](localhost:9090/graph) to run PromQL queries
    - [localhost:9090/metrics](localhost:9090/metrics) to scrape internal metrics of Prometheus
    - [localhost:9090/targets](localhost:9090/targets) to view status of scraping services
 - Grafana (optional) on [localhost:3000](localhost:3000) to visualize Prometheus metrics.

    _Default Grafana credentials: admin/admin_
 - Celery Flower (optional) on [localhost:5555](localhost:5555) a dashboard for Celery task status, retries, queue depth etc monitoring


## FastAPI Endpoints
### 1. Submit Image for Classification
```http
POST /classify
Content-Type: multipart/form-data

{
  "image": <image_file>,
  "webhook_url": "https://webhook.site/<webhook_id>" (optional)
}
```
*Response:*
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Image classification task submitted successfully"
}
```

### 2. Check Task Status
```http
GET /task-status/{task_id}
```
*Response:*
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "predictions": [
      {
        "class": "Golden retriever",
        "confidence": 0.8945
      },
      {
        "class": "Labrador retriever", 
        "confidence": 0.0823
      }
    ],
    "processing_time": 2.34,
    "image_url": "http://minio:9000/images/image_123.jpg"
  }
}
```
___
# Monitoring (Prometheus + Grafana)

## PromQL (Prometheus Query Language)

`GET http://localhost:8000/metrics/`

Prometheus Queries includes:

- *image_task_success_total*: Total number of successful image classifications
- *image_task_failure_total*: Total number of failed image classifications
- *image_task_latency_seconds*: Task processing latency histogram
- *webhook_success_total*: Successful webhook deliveries
- *webhook_failure_total*: Failed webhook deliveries
- *webhook_latency_seconds*: Webhook delivery latency
- *celery_queue_depth*: Current queue depth

Example: `curl -s http://localhost:8000/metrics | grep 'image_task_success_total'`

Note: In prometheus.yml port for docker use needs the container name `- targets: ['api:8000']` but for local deployment `- targets: ['localhost:8000']`
