import uvicorn
from fastapi import FastAPI
from api.routes import router
from prometheus_client import start_http_server
from utils.config import PROM_PORT
from utils.logger import logger

app = FastAPI(title="Celery Image Pipeline API")

# Mount routes
app.include_router(router, prefix="/api")

@app.on_event("startup")
def startup_event():
    # Start Prometheus metrics endpoint
    start_http_server(PROM_PORT)
    logger.info(f"Prometheus metrics available at :{PROM_PORT}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
