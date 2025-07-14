import os
import uvicorn
from fastapi import FastAPI, Response
from prometheus_client import (
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST, multiprocess, REGISTRY
)
from prometheus_fastapi_instrumentator import Instrumentator

from api.routes import router
from utils.logger import logger
from services.storage import get_minio_client

app = FastAPI(title="Celery Image Pipeline API")
app.include_router(router, prefix="/api")

# Setup Prometheus multiprocess directory
MP_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR", "/tmp/metrics-multiproc")
os.makedirs(MP_DIR, exist_ok=True)

# Instrumentator for automatic FastAPI route metrics
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    env_var_name="ENABLE_METRICS",
)
instrumentator.instrument(app).expose(app, include_in_schema=False)

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    registry = CollectorRegistry()
    try:
        multiprocess.MultiProcessCollector(registry)
        data = generate_latest(registry)
    except Exception as e:
        logger.warning(f"Multiproc metrics failed: {e}, falling back to default REGISTRY")
        data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.on_event("startup")
def startup_event():
    logger.info("Prometheus metrics exposed at /metrics")
    get_minio_client()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
