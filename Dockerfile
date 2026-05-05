# syntax=docker/dockerfile:1
# Multi-stage: faster rebuilds (cached deps layer), smaller & safer final image (no gcc, non-root).

# ── Stage 1: install Python deps into a dedicated venv ───────────────────────
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Toolchain only in this stage (native wheels / cryptography / asyncpg build fallback)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
COPY src ./src/
COPY frontend ./frontend/

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir ".[server]"

# ── Stage 2: minimal runtime — no compilers; ffmpeg for audio ingestion ─────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (fixed uid/gid for volume ownership if needed)
RUN useradd --create-home --uid 1000 --user-group --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv

COPY --chown=app:app alembic.ini .
COPY --chown=app:app src/ ./src/

RUN mkdir -p data/recordings data/meeting-audio \
    && chown -R app:app /app/data

USER app

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
