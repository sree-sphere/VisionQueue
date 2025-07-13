from loguru import logger
import sys

# Configure loguru: stdout + file with rotation
logger.remove()
logger.add(sys.stdout, level="INFO", enqueue=True)
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    enqueue=True,
)
