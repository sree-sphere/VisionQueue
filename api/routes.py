from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from services.storage import upload_image
from services.task_handler import submit_pipeline
from utils.logger import logger
import uuid
import json

router = APIRouter()

@router.post("/upload-image")
async def upload_image_endpoint(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    callback_url: str = Query(
        default=None,
        title="Callback Webhook URL",
        description="Optional webhook URL to notify on task completion via POST",
        example="https://webhook.site/test-url"
    ),
     metadata: str = Query(
        default=None,
        title="Image Metadata (JSON)",
        description="Optional JSON string containing metadata about the image",
        example='{"source": "user", "label": "test"}'
    ),
):
    """
    Accepts an image, uploads to MinIO, and triggers the Celery pipeline.
    """
    contents = await file.read()
    ext = file.filename.split(".")[-1].lower()

    if ext not in ("jpg", "jpeg", "png"):
        logger.warning(f"Rejected file {file.filename} with unsupported type '{ext}'")
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Generate unique object name for storage
    object_name = f"{uuid.uuid4()}.{ext}"
    content_type = f"image/{'jpeg' if ext == 'jpg' else ext}"

    try:
        image_url = upload_image(contents, object_name, content_type=content_type)
        logger.info(f"Uploaded {file.filename} as {object_name} to {image_url}")
    except Exception as e:
        logger.exception("Image upload failed")
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    # Prepare metadata for the pipeline
    try:
        metadata_dict = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        logger.error("Invalid metadata JSON")
        raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    metadata_dict.update({
        "filename": file.filename,
        "object_name": object_name,
        "url": image_url
    })

    # Trigger Celery pipeline
    logger.info(f"Received callback_url: {callback_url}")
    async_result = submit_pipeline(contents, metadata_dict, callback_url)
    if async_result is None or not hasattr(async_result, "id"):
        logger.error("Pipeline submission failed: async_result is None or missing 'id'")
        raise HTTPException(status_code=500, detail="Pipeline submission failed")
    logger.info(f"Pipeline submitted: task_id={async_result.id}")

    return JSONResponse({"task_id": async_result.id})

@router.get("/task-status/{task_id}")
def task_status(task_id: str):
    """
    Check Celery task status and get classification result.
    """
    from services.celery_worker import celery_app
    res = celery_app.AsyncResult(task_id)

    if res.state == "PENDING":
        return {"state": res.state, "status": "Task is waiting in queue"}
    elif res.state in ("FAILURE", "REVOKED"):
        return {"state": res.state, "error": str(res.result)}
    elif res.state == "SUCCESS":
        return {
            "state": res.state,
            "result": res.result  # this should contain classification result
        }
    else:
        return {"state": res.state, "status": "Task is running"}
