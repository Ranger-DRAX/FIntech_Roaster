# ---- Dockerfile ----

# ---------- BASE ----------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system deps (psycopg2 needs libpq)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        curl && \
    rm -rf /var/lib/apt/lists/*

# ---------- DEPENDENCIES ----------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- APPLICATION ----------
COPY . .

# ---------- ENTRYPOINT ----------
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "djangoInternals.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]