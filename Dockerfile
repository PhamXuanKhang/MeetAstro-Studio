FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project metadata first (layer cache: deps change less often than code)
COPY pyproject.toml .

# Cài server dependencies qua pyproject.toml optional group
RUN pip install --no-cache-dir ".[server]"

# Copy source code
COPY src/ ./src/
COPY alembic.ini .

# Thư mục lưu audio uploads từ desktop client
RUN mkdir -p data/recordings

ENV PYTHONPATH=/app

EXPOSE 8000
