# main.py

import os
import shutil
import uvicorn
from fastapi import FastAPI, Response
from prometheus_client import (
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST, multiprocess
)
from api.routes import router
from utils.logger import logger

app = FastAPI(title="Celery Image Pipeline API")
app.include_router(router, prefix="/api")

# Clean up stale files if running multiple times
MP_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR", "/tmp/metrics-multiproc")
if os.path.isdir(MP_DIR):
    for fname in os.listdir(MP_DIR):
        os.remove(os.path.join(MP_DIR, fname))
else:
    os.makedirs(MP_DIR, exist_ok=True)

@app.get("/metrics")
def metrics():
    # Create a registry and merge multi-process files
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.on_event("startup")
def startup_event():
    logger.info("Prometheus multiprocess metrics available at /metrics")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
