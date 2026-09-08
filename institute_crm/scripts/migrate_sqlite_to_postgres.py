#!/usr/bin/env python
"""
One-off helper: copy data out of the legacy ``db.sqlite3`` into PostgreSQL.

Only needed if you have local data in the old SQLite file worth keeping. If you are
happy to start fresh, skip this entirely and use ``seed_data.py`` instead.

Because ``settings.py`` now hard-requires PostgreSQL, the SQLite side is read through a
throwaway settings override rather than the project's own database configuration.

Usage
-----
    # 1. From institute_crm/, with the virtualenv active and .env pointing at PostgreSQL:
    python scripts/migrate_sqlite_to_postgres.py --dump

    # 2. Inspect data_dump.json, then apply the schema to PostgreSQL:
    python manage.py migrate

    # 3. Load it:
    python scripts/migrate_sqlite_to_postgres.py --load

Notes
-----
* ContentType and Permission rows are excluded; Django recreates them during migrate,
  and including them causes primary-key collisions.
* Run against an *empty* PostgreSQL database. Loading into a seeded database will fail
  on unique constraints.
* This is a convenience tool, not a supported migration path for production data.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DUMP_PATH = BASE_DIR / "data_dump.json"
SQLITE_PATH = BASE_DIR / "db.sqlite3"

EXCLUDE = [
    "contenttypes",
    "auth.permission",
    "admin.logentry",
    "sessions.session",
]

APP_LABELS = [
    "accounts",
    "users_profiles",
    "crm_leads",
    "academics",
    "assignments_exams",
    "finance",
    "communications",
]


def _run(args: list[str], env: dict[str, str] | None = None) -> int:
    printable = " ".join(args)
    print(f"\n$ {printable}\n", flush=True)
    return subprocess.call(args, cwd=BASE_DIR, env=env)


def dump() -> int:
    if not SQLITE_PATH.is_file():
        print(f"No SQLite database found at {SQLITE_PATH}. Nothing to migrate.")
        return 1

    # Point Django at SQLite just for this subprocess. The main settings module forbids
    # it, so a dedicated read-only settings shim is used instead.
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "scripts.sqlite_readonly_settings"
    env["PYTHONPATH"] = str(BASE_DIR)

    args = [sys.executable, "-m", "django", "dumpdata", "--natural-foreign", "--natural-primary",
            "--indent", "2", "--output", str(DUMP_PATH), *APP_LABELS]
    code = _run(args, env=env)
    if code == 0:
        print(f"\nWrote {DUMP_PATH}. Review it, run `python manage.py migrate`, then --load.")
    return code


def load() -> int:
    if not DUMP_PATH.is_file():
        print(f"No dump found at {DUMP_PATH}. Run with --dump first.")
        return 1
    return _run([sys.executable, "manage.py", "loaddata", str(DUMP_PATH)])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dump", action="store_true",
                      help="Export the legacy SQLite data to data_dump.json")
    group.add_argument("--load", action="store_true",
                      help="Import data_dump.json into the configured PostgreSQL database")
    parsed = parser.parse_args()
    return dump() if parsed.dump else load()


if __name__ == "__main__":
    raise SystemExit(main())
