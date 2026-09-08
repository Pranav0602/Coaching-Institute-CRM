#!/usr/bin/env bash
# Render build script for Django backend
set -o errexit

pip install --no-cache-dir -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Optional: seed initial roles/branches on first deploy (idempotent)
# python seed_data.py
