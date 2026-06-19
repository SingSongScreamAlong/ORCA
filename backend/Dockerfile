# ORCA backend image.
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --upgrade pip && pip install .

# Migrations and config (mounted or copied as needed).
COPY alembic.ini ./
COPY migrations ./migrations
COPY db ./db

EXPOSE 8000

# The default in-memory backend needs no database to start.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
