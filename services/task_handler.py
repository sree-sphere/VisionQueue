"""
Defines Celery tasks: preprocessing, classification, storage, webhook.
"""

import time
import requests
from celery import chain
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge

from services.celery_worker import celery_app
from core.classifier import preprocess_image, classify
from utils.logger import logger
from utils.config import WEBHOOK_TIMEOUT

# Task metrics with labels
TASK_SUCCESS = Counter("image_task_success_total", "Successful image tasks", ["task_name"])
TASK_FAILURE = Counter("image_task_failure_total", "Failed image tasks", ["task_name"])
TASK_LATENCY = Histogram("image_task_latency_seconds", "Latency of image tasks", ["task_name"])
QUEUE_DEPTH = Gauge("celery_queue_depth", "Number of tasks in queue")

# Webhook metrics
WEBHOOK_SUCCESS = Counter("webhook_success_total", "Successful webhook sends")
WEBHOOK_FAILURE = Counter("webhook_failure_total", "Failed webhook sends")
WEBHOOK_LATENCY = Histogram("webhook_latency_seconds", "Latency of webhook POST request")


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def preprocess(self, image_bytes: bytes):
    task_name = "preprocess"
    logger.info(f"[{self.request.id}] Preprocessing image")
    start = time.time()
    try:
        result = preprocess_image(image_bytes)
        TASK_SUCCESS.labels(task_name=task_name).inc()
        return result
    except Exception as e:
        TASK_FAILURE.labels(task_name=task_name).inc()
        raise self.retry(exc=e)
    finally:
        TASK_LATENCY.labels(task_name=task_name).observe(time.time() - start)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def classify_task(self, image_tensor):
    task_name = "classify_task"
    logger.info(f"[{self.request.id}] Classifying image")
    start = time.time()
    try:
        result = classify(image_tensor)
        TASK_SUCCESS.labels(task_name=task_name).inc()
        return result
    except Exception as e:
        TASK_FAILURE.labels(task_name=task_name).inc()
        raise self.retry(exc=e)
    finally:
        TASK_LATENCY.labels(task_name=task_name).observe(time.time() - start)


@celery_app.task(bind=True)
def store_result(self, classification, metadata: dict):
    """
    Stores classification result in PostgreSQL and returns the full result.
    """
    task_name = "store_result"
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

    start = time.time()
    try:
        with engine.connect() as conn:
            ins = results.insert().values(task_id=self.request.id, payload=full_result)
            conn.execute(ins)
            logger.info(f"[{self.request.id}] Stored result")
            TASK_SUCCESS.labels(task_name=task_name).inc()
    except Exception as e:
        TASK_FAILURE.labels(task_name=task_name).inc()
        logger.error(f"[{self.request.id}] Failed to store result: {e}")
        raise self.retry(exc=e)
    finally:
        TASK_LATENCY.labels(task_name=task_name).observe(time.time() - start)

    return full_result


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3}
)
def send_webhook(self, full_result: dict, callback_url: str):
    """
    Sends classification result to callback_url, records metrics, and returns the payload.
    """
    task_name = "send_webhook"
    logger.info(f"[{self.request.id}] Sending webhook to {callback_url}")
    start = time.time()
    try:
        resp = requests.post(callback_url, json=full_result, timeout=WEBHOOK_TIMEOUT)
        resp.raise_for_status()
        WEBHOOK_SUCCESS.inc()
        TASK_SUCCESS.labels(task_name=task_name).inc()
        logger.info(f"[{self.request.id}] Webhook sent ({resp.status_code}) to {callback_url}")
    except Exception as e:
        WEBHOOK_FAILURE.inc()
        TASK_FAILURE.labels(task_name=task_name).inc()
        logger.error(f"[{self.request.id}] Webhook failed: {e}")
        raise self.retry(exc=e)
    finally:
        WEBHOOK_LATENCY.observe(time.time() - start)
        TASK_LATENCY.labels(task_name=task_name).observe(time.time() - start)

    return full_result


def submit_pipeline(image_bytes: bytes, metadata: dict, callback_url: Optional[str] = None):
    """
    Orchestrates: preprocess -> classify -> store_result -> (optional send_webhook).
    Returns AsyncResult for the final task so result() always holds full_result.
    """
    try:
        reserved = celery_app.control.inspect().reserved() or {}
        QUEUE_DEPTH.set(sum(len(v) for v in reserved.values()))
    except Exception as e:
        logger.warning(f"Could not inspect broker: {e}")

    # Build the pipeline
    workflow = chain(
        preprocess.s(image_bytes),
        classify_task.s(),
        store_result.s(metadata)
    )

    if callback_url:
        logger.info(f"Callback URL provided: {callback_url}")
        workflow = workflow | send_webhook.s(callback_url)
    else:
        logger.info("No callback URL provided")

    return workflow.apply_async()
