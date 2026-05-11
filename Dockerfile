# syntax=docker/dockerfile:1
# Multi-stage: cached Python deps, built landing page assets, smaller runtime image.

# Stage 1: build landing page static assets
FROM node:20-slim AS website-builder

WORKDIR /website

COPY website/package*.json ./
RUN npm ci

COPY website/ ./
RUN npm run build

# Stage 2: install Python deps into a dedicated venv
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
COPY src ./src/

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir ".[server]"

# Stage 3: minimal runtime ? no compilers; ffmpeg for audio ingestion
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 --user-group --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app src/ ./src/
COPY --from=website-builder --chown=app:app /website/dist ./website/dist/

RUN mkdir -p data/recordings data/meeting-audio downloads \
    && chown -R app:app /app/data /app/downloads

USER app

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
