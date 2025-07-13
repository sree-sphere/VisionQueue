import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL
from utils.logger import logger

# Load .env explicitly and log the path
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path)
logger.debug(f"Loaded environment from: {env_path}")

# Helper to log critical vars
def log_env_var(key: str, required: bool = True):
    val = os.getenv(key)
    if val is None:
        if required:
            logger.warning(f"{key} is NOT set!")
        else:
            logger.debug(f"{key} is not set (optional)")
    else:
        logger.info(f"{key}={val}")
    return val

# PostgreSQL
PG_HOST = log_env_var("PG_HOST")
PG_USER = log_env_var("PG_USER")
PG_PASSWORD = log_env_var("PG_PASSWORD")
PG_DB = log_env_var("PG_DB")
PG_PORT = int(os.getenv("PG_PORT", 5432))
logger.info(f"PG_PORT={PG_PORT}")

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=PG_USER,
    password=PG_PASSWORD,
    host=PG_HOST,
    port=PG_PORT,
    database=PG_DB,
)

# Celery
CELERY_BROKER_URL = log_env_var("CELERY_BROKER_URL", required=False)
CELERY_RESULT_BACKEND = log_env_var("CELERY_RESULT_BACKEND", required=False)

# Model
MODEL_NAME = os.getenv("MODEL_NAME", "resnet18")
logger.info(f"MODEL_NAME={MODEL_NAME}")

# MinIO/S3
MINIO_ENDPOINT = log_env_var("MINIO_ENDPOINT", required=False)
MINIO_ACCESS_KEY = log_env_var("MINIO_ACCESS_KEY", required=False)
MINIO_SECRET_KEY = log_env_var("MINIO_SECRET_KEY", required=False)
MINIO_BUCKET = log_env_var("MINIO_BUCKET", required=False)

# Prometheus
PROM_PORT = int(os.getenv("PROM_PORT", 8000))
logger.info(f"PROM_PORT={PROM_PORT}")

# Webhook
WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", 5))
logger.info(f"WEBHOOK_TIMEOUT={WEBHOOK_TIMEOUT}")
