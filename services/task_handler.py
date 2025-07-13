"""
Defines Celery tasks: preprocessing, classification, storage, webhook.
"""

import requests
from celery import chord
from services.celery_worker import celery_app
from core.classifier import preprocess_image, classify
from utils.logger import logger
from utils.config import WEBHOOK_TIMEOUT
from prometheus_client import Counter, Histogram, Gauge

# Metrics
TASK_SUCCESS = Counter("image_task_success_total", "Successful image tasks")
TASK_FAILURE = Counter("image_task_failure_total", "Failed image tasks")
TASK_LATENCY = Histogram("image_task_latency_seconds", "Latency of image tasks")
QUEUE_DEPTH = Gauge("celery_queue_depth", "Number of tasks in queue")

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def preprocess(self, image_bytes: bytes):
    logger.info(f"Preprocessing image in task {self.request.id}")
    return preprocess_image(image_bytes)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def classify_task(self, image_tensor):
    logger.info(f"Classifying image in task {self.request.id}")
    return classify(image_tensor)

@celery_app.task(bind=True)
def store_result(self, classification, metadata: dict):
    """
    Stores classification result in PostgreSQL and returns the full result.
    """
    from sqlalchemy import create_engine, Table, Column, Integer, String, JSON, MetaData
    from utils.config import DATABASE_URL

    engine = create_engine(DATABASE_URL)
    meta = MetaData()
    results = Table(
        "results", meta,
        Column("id", Integer, primary_key=True),
        Column("task_id", String, unique=True),
        Column("payload", JSON),
    )
    meta.create_all(engine)

    full_result = {
        "task_id": self.request.id,
        "metadata": metadata,
        "classification": classification
    }

    try:
        with engine.connect() as conn:
            ins = results.insert().values(
                task_id=self.request.id,
                payload=full_result
            )
            conn.execute(ins)
            logger.info(f"Stored result for task {self.request.id}")
    except Exception as e:
        logger.error(f"Failed to store result: {e}")
        raise self.retry(exc=e)

    # ✅ return full result so it's visible via /task-status/<id>
    return full_result

@celery_app.task(bind=True)
def send_webhook(self, result, callback_url: str):
    try:
        requests.post(callback_url, json=result, timeout=WEBHOOK_TIMEOUT)
        logger.info(f"Webhook sent for task {self.request.id} to {callback_url}")
    except Exception as e:
        logger.error(f"Webhook failed: {e}")


def submit_pipeline(image_bytes: bytes, metadata: dict, callback_url: str = None):
    """
    Orchestrates the full pipeline: preprocess → classify → store → (optional webhook).
    Returns the AsyncResult of the store_result task or the chain.
    """
    # record queue depth (example; actual scraping of queue length may need broker API)
        # update queue depth metric (stubbed if no broker)
    try:
        reserved = celery_app.control.inspect().reserved() or {}
        QUEUE_DEPTH.set(sum(len(v) for v in reserved.values()))
    except Exception as e:
        # broker not configured / not reachable → skip metric
        logger.warning(f"Could not inspect Celery broker: {e}")


    inner_pipeline = chord(
        [preprocess.s(image_bytes) | classify_task.s()],
        store_result.s(metadata)
    )
    # result = inner_pipeline.delay()

    if callback_url:
        logger.info(f"Callback URL provided: {callback_url}")
        result = chord(
            [inner_pipeline],
            send_webhook.s(callback_url)
        ).delay()
    else:
        result = inner_pipeline.delay()
        logger.info("No callback URL provided")

    return result
