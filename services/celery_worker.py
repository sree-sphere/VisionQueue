from celery import Celery
from utils.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
from utils.logger import logger
# from services.task_handler import preprocess 
# Define Celery app
celery_app = Celery(
    "image_pipeline",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["services.task_handler"]
)

# Global Celery configuration
celery_app.conf.update(
    task_acks_late=True,         # Acknowledge only after success
    worker_prefetch_multiplier=1,
    task_default_retry_delay=10, # seconds
    task_routes={                # dead-letter exchange pattern (example)
        "services.task_handler.*": {"queue": "image_tasks"},
    },
    task_default_queue="image_tasks",
    task_default_exchange="image",
    task_default_exchange_type="direct",
    task_default_routing_key="image",
)

# Ensure logger is available in tasks
celery_app.logger = logger
import services.task_handler
print("Registered tasks:", celery_app.tasks.keys())
