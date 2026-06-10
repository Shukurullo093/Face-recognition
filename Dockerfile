# syntax=docker/dockerfile:1.7
# CUDA 12.x runtime base compatible with onnxruntime-gpu 1.20
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH"

# System deps: python3.12, libs needed by opencv + onnxruntime
RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && apt-get install -y --no-install-recommends \
        python3.12 python3.12-venv python3.12-dev \
        libgl1 libglib2.0-0 curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN python3.12 -m venv /opt/venv && pip install --upgrade pip setuptools wheel

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
