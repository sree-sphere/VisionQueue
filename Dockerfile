# Dockerfile

ARG PYTHON_VERSION=3.12.7
FROM python:${PYTHON_VERSION}-slim AS base

# Prevent .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create non‑root user
ARG UID=10001
RUN adduser \
      --disabled-password \
      --gecos "" \
      --home "/home/appuser" \
      --shell "/sbin/nologin" \
      --no-create-home \
      --uid "${UID}" \
      appuser \
  && mkdir -p /home/appuser \
  && chown -R appuser:appuser /home/appuser

# Install system deps and Python requirements
USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libpq-dev \
 && pip install --no-cache-dir -r requirements.txt \
 && apt-get purge -y gcc \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

RUN pip install python-multipart celery[redis] flower prometheus-fastapi-instrumentator

# Prepare log and metrics dirs (give appuser ownership)
RUN mkdir -p /app/logs \
    && mkdir -p /tmp/metrics-multiproc \
    && chown -R appuser:appuser /app/logs /tmp/metrics-multiproc

# Copy code and switch to non‑root
COPY . .
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
