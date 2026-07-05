#!/bin/bash
# ---- docker-entrypoint.sh ----

set -e  # Exit immediately on error

echo "→ Running database migrations..."
python manage.py migrate --noinput

echo "→ Collecting static files..."
python manage.py collectstatic --noinput

echo "→ Starting server..."
exec "$@"