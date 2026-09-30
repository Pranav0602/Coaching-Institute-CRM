#!/usr/bin/env bash
# Render build script for Django backend
set -o errexit

pip install --no-cache-dir -r requirements.txt

python manage.py collectstatic --noinput

# `migrate` above is what applies the token_blacklist tables. Those tables are a hard
# dependency of login while JWT_BLACKLIST is on - SimpleJWT writes an OutstandingToken row
# for every refresh token it issues - so a build that skipped them would deploy code that
# 500s on every sign-in.
python manage.py migrate --noinput

# `--deploy` is required, not decorative. Django runs deploy=True checks (crm.E004,
# crm.E003) *only* under this flag; plain `migrate` and `collectstatic` skip them. An
# earlier version of this script relied on them and stopped no deploys at all.
python manage.py check --deploy

# One readable line in the deploy log instead of a check's wall of text, and a build
# failure with an actionable message. Run `python manage.py check --deploy` manually to see
# the same state, or `python scripts/check_token_blacklist.py` for just this one check.
python scripts/check_token_blacklist.py

# Note: a failed build leaves the previous deploy serving, and that deploy may be the one
# 500ing on login. Workers create these tables at boot (institute_crm/token_revocation.py),
# so the next successful deploy repairs the database regardless - but a failing build step
# is a signal to investigate, not something to leave in place.

# Optional: seed initial roles/branches on first deploy (idempotent)
# python seed_data.py
