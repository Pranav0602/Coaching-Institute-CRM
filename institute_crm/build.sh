#!/usr/bin/env bash
# Render build script for Django backend
set -o errexit

pip install --no-cache-dir -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# `migrate` above is what applies the token_blacklist tables. Those tables are a
# hard dependency of login while JWT_BLACKLIST is on - SimpleJWT writes an
# OutstandingToken row for every refresh token it issues - so a build that
# skipped them would deploy code that 500s on every sign-in. crm.E004 makes that
# combination a build failure; this prints one readable line into the deploy log
# and fails the build too, with an actionable message.
python scripts/check_token_blacklist.py

# Optional: seed initial roles/branches on first deploy (idempotent)
# python seed_data.py
