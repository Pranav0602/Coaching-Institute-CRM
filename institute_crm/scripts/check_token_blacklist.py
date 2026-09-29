"""Confirm token revocation is actually usable against this database.

Called from ``build.sh`` immediately after ``manage.py migrate``. The system check
``crm.E004`` already turns a missing-table deploy into a build failure, but a
check's output is a wall of text; this prints one line an operator can read in
the deploy log, and it is runnable by hand against a live database:

    python scripts/check_token_blacklist.py

Exit code 0 means the configuration in use is coherent. Exit code 1 means login
will 500 until the migrations are applied (or ``JWT_BLACKLIST`` is turned off).
"""
import os
import sys

import django

# This file lives in <project-root>/scripts/, so the project root — the directory
# holding manage.py and the institute_crm package — is one level up.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "institute_crm.settings")
django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection  # noqa: E402

TABLE = "token_blacklist_outstandingtoken"


def main() -> int:
    if not getattr(settings, "JWT_BLACKLIST", False):
        print("[ok] JWT_BLACKLIST is off; refresh tokens expire rather than being revoked.")
        print("     Login does not depend on any token_blacklist table.")
        return 0

    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s)", [f"public.{TABLE}"])
        found = (cursor.fetchone() or (None,))[0]

    if not found:
        print(f"[FAIL] JWT_BLACKLIST is on but {TABLE} does not exist.", file=sys.stderr)
        print("       Every login will fail with a 500, because SimpleJWT writes an")
        print("       OutstandingToken row each time it issues a refresh token.")
        print("       Fix:  python manage.py migrate   (against the service database)")
        print("   or:  set JWT_BLACKLIST=false and redeploy.", file=sys.stderr)
        return 1

    print(f"[ok] {TABLE} present; refresh-token revocation is active.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
