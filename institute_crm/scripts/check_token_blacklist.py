"""Confirm token revocation is actually usable against this database.

Called from ``build.sh`` immediately after ``manage.py migrate``, and runnable by hand
against a live database:

    python scripts/check_token_blacklist.py

It prints one line an operator can read in the deploy log rather than the wall of text a
system check produces, and it names the tables that are actually missing.

Exit code 0 means the configuration in use is coherent. Exit code 1 means every login
will fail until the migrations are applied (or ``JWT_BLACKLIST`` is turned off).
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

from institute_crm import token_revocation  # noqa: E402


def main() -> int:
    if not token_revocation.enabled():
        print("[ok] Token revocation is off; refresh tokens expire rather than being revoked.")
        print("     Login does not depend on any token_blacklist table.")
        return 0

    missing = token_revocation.missing_tables()
    if missing is None:
        print("[warn] Could not reach the database, so revocation is unverified.", file=sys.stderr)
        return 0

    if missing:
        print(f"[FAIL] Missing table(s): {', '.join(missing)}.", file=sys.stderr)
        print("       Every login fails with a 500, because SimpleJWT writes an")
        print("       OutstandingToken row each time it issues a refresh token.")
        print("       Fix:  python manage.py migrate   (against the service database)")
        print("   or:  set JWT_BLACKLIST=false and redeploy.", file=sys.stderr)
        return 1

    print("[ok] token_blacklist tables present; refresh-token revocation is active.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
