#!/usr/bin/env bash
# Render build script for Django backend
set -o errexit

pip install --no-cache-dir -r requirements.txt

python manage.py collectstatic --noinput

# `migrate` is what applies ALL app tables (accounts, communications.sender/batch,
# token_blacklist, ...). A build that skips it deploys code against a stale schema
# (e.g. `column communications_notification.sender_id does not exist`) and every
# affected endpoint 500s.
python manage.py migrate --noinput

# Fail the build if any migration is still unapplied (e.g. migrate pointed at a
# different DATABASE_URL than the runtime). `migrate --noinput` above should leave
# zero planned migrations; a non-empty plan means the schema drifted.
if python manage.py showmigrations --plan | grep -q "\[ \]"; then
  echo "ERROR: unapplied migrations remain after migrate. Refusing to deploy with a stale schema."
  python manage.py showmigrations --plan | grep "\[ \]" || true
  exit 1
fi

# Catch model changes that shipped without a migration file at all.
python manage.py makemigrations --check --dry-run

# `--deploy` is required, not decorative. Django runs deploy=True checks (crm.E003,
# crm.E004, crm.E005) *only* under this flag; plain `migrate` and `collectstatic`
# skip them. An earlier version of this script relied on them and stopped no deploys
# at all.
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
