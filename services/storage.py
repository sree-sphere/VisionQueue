import io
from urllib.parse import urlparse
from minio import Minio
from minio.error import S3Error
from loguru import logger
from utils.config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET,
)

# Global client cache
_client = None
_host = None
_port = None

# Parse endpoint (no scheme), handle formats like "localhost:9000" or "https://..."
def init_minio_client():
    if not MINIO_ENDPOINT:
        raise ValueError("MINIO_ENDPOINT is not set or is None")
    
    parsed = urlparse(MINIO_ENDPOINT if MINIO_ENDPOINT.startswith(("http://", "https://")) else f"http://{MINIO_ENDPOINT}")
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    secure = (parsed.scheme == "https")

    logger.debug(f"Initializing Minio client -> host={host}, port={port}, secure={secure}")

    client = Minio(
        f"{host}:{port}",
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=secure,
    )

    # Verify connection
    client.list_buckets()

    # Ensure bucket exists
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)

    return client, host, port

# Lazy-load MinIO client
def get_minio_client():
    global _client, _host, _port
    if _client is None:
        try:
            _client, _host, _port = init_minio_client()
            logger.info(f"Connected to MinIO at {_host}:{_port}")
        except Exception as e:
            logger.critical(f"Cannot connect to MinIO: {e}")
            raise

        # Ensure bucket exists
        try:
            if not _client.bucket_exists(MINIO_BUCKET):
                _client.make_bucket(MINIO_BUCKET)
                logger.info(f"Created bucket '{MINIO_BUCKET}'")
            else:
                logger.debug(f"Bucket '{MINIO_BUCKET}' already exists")
        except S3Error as e:
            logger.error(f"Bucket operation error on '{MINIO_BUCKET}': {e}")
            raise

    return _client, _host, _port

# Upload function
def upload_image(image_bytes: bytes, object_name: str, content_type: str = "image/jpeg") -> str:
    """
    Upload image to MinIO using object_name (uuid.ext).
    """
    logger.info(f"Uploading '{object_name}' to bucket '{MINIO_BUCKET}'")
    stream = io.BytesIO(image_bytes)
    stream.seek(0)
    
    client, host, port = get_minio_client()

    try:
        client.put_object(
            MINIO_BUCKET,
            object_name,  # use the unique uuid.ext here
            data=stream,
            length=len(image_bytes),
            content_type=content_type,
        )
        logger.debug(f"Uploaded {object_name} ({len(image_bytes)} bytes)")
    except S3Error as e:
        logger.error(f"Failed to upload '{object_name}': {e}")
        raise

    return f"http://{host}:{port}/{MINIO_BUCKET}/{object_name}"
