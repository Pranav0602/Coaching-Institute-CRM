"""
Throwaway settings module used **only** by ``scripts/migrate_sqlite_to_postgres.py``
to read the legacy ``db.sqlite3`` file during a one-off data export.

This is not an escape hatch from the project's PostgreSQL requirement:

* It is never importable as the running application's settings - it omits the REST
  framework, middleware, CORS and JWT configuration the API depends on.
* It is only ever selected by that one script, in a subprocess, for ``dumpdata``.
* ``institute_crm.settings`` remains the sole settings module for every other purpose
  and still refuses any non-PostgreSQL engine.

Delete this file (and the script) once the legacy SQLite database is gone.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "sqlite-export-only-not-a-real-secret"
DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "users_profiles",
    "crm_leads",
    "academics",
    "assignments_exams",
    "finance",
    "communications",
]

# The only place in this repository where a SQLite engine is permitted, and only for
# reading the historical file.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {},
    }
}

AUTH_USER_MODEL = "accounts.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"
STATIC_URL = "static/"

# `accounts.apps.AccountsConfig.ready()` registers institute_crm.checks, which asserts a
# PostgreSQL engine. dumpdata does not run system checks, but silence the logger anyway.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"]},
}
