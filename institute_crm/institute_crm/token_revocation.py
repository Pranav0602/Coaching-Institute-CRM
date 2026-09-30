"""
Is refresh-token revocation actually usable against the database in use?

Why this module exists
----------------------
``JWT_BLACKLIST`` installs ``rest_framework_simplejwt.token_blacklist``, which ships two
tables - ``token_blacklist_outstandingtoken`` and ``token_blacklist_blacklistedtoken``.
Once it is installed, ``RefreshToken.for_user`` inserts an ``OutstandingToken`` row on
*every* token issuance, sign-in included, and ``RefreshToken.verify`` queries
``BlacklistedToken`` on every refresh. So the switch is not merely "a feature that turns
on when its tables arrive": **login cannot complete at all until they do.**

That turns a forgotten migration into a total outage with a bare PostgreSQL traceback as
the only evidence, which is exactly how this reached production. The defences are spread
across the deploy pipeline, the readiness probe and the token issuance path, so the
answer to "is revocation usable right now?" lives here and is computed once per process:

* :func:`missing_tables` - what the connected database is actually missing.
* :func:`usable` - the cached yes/no the issuance path asks, once per process.
* :func:`repair_missing_tables` - applied at worker boot, see ``wsgi.py``.

The probe reads the tables from the installed models' ``_meta.db_table`` and asks Django's
introspection for what exists, so it does not hard-code a schema (``public.``) that a
managed database is free to rename.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections

logger = logging.getLogger("institute_crm.token_revocation")

#: The SimpleJWT app that owns the two tables. Matches ``JWT_BLACKLIST`` in settings.py.
BLACKLIST_APP = "rest_framework_simplejwt.token_blacklist"

#: Arbitrary but stable key for the advisory lock that serialises the boot-time repair.
#: Session-scoped, so it is released even if the unlocking statement never runs.
ADVISORY_LOCK_KEY = 8_147_233_901

#: Cached answer to :func:`usable`. ``None`` until the first probe. The schema does not
#: change under a running worker, so one probe per process is enough - and a per-login
#: introspection query on the hot path would be pure overhead.
_usable_cache: bool | None = None


def enabled() -> bool:
    """Whether revocation is switched on *and* the app that implements it is installed."""
    return bool(getattr(settings, "JWT_BLACKLIST", False)) and BLACKLIST_APP in settings.INSTALLED_APPS


def required_tables() -> list[str]:
    """Table names revocation depends on, taken from the installed models."""
    if not apps.is_installed(BLACKLIST_APP):
        return []
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )

    return [OutstandingToken._meta.db_table, BlacklistedToken._meta.db_table]


def missing_tables(alias: str = DEFAULT_DB_ALIAS) -> list[str] | None:
    """Required tables that are absent, or ``None`` when the database is unreachable.

    ``None`` means "cannot tell", which is a different problem from "absent" and must not
    be reported as a missing table: a database outage should not be described as a
    migration that was forgotten.
    """
    wanted = required_tables()
    if not wanted:
        return []
    connection = connections[alias]
    try:
        with connection.cursor() as cursor:
            present = set(connection.introspection.table_names(cursor))
    except DatabaseError as exc:
        logger.warning("Could not probe the token_blacklist tables: %s", exc)
        return None
    return [table for table in wanted if table not in present]


def usable(alias: str = DEFAULT_DB_ALIAS) -> bool:
    """Whether a refresh token can be recorded and revoked right now.

    Logs once per process when the answer is no, because that state is invisible from the
    outside - tokens still work, they just stop being revocable - and it is exactly the
    thing that went unnoticed before.
    """
    global _usable_cache

    if _usable_cache is None:
        missing = missing_tables(alias)
        # An unreachable database is not a reason to stop issuing tokens; the request that
        # needed it is already failing on its own queries with a far clearer error.
        _usable_cache = missing is None or not missing
        if missing:
            logger.error(
                "Refresh-token revocation is OFF because %s %s absent. Login still "
                "works, but sessions expire instead of being revoked. Fix with: "
                "python manage.py migrate   (or set JWT_BLACKLIST=false to make this "
                "the intended configuration).",
                ", ".join(missing),
                "is" if len(missing) == 1 else "are",
            )
    return _usable_cache


def reset_cache() -> None:
    """Forget the cached probe result. For tests, and after :func:`repair_missing_tables`."""
    global _usable_cache

    _usable_cache = None


@contextmanager
def _advisory_lock(alias: str = DEFAULT_DB_ALIAS) -> Iterator[None]:
    """Serialise the repair across gunicorn workers and any second instance.

    ``migrate`` is not safe to run concurrently: two workers reaching the same unmigrated
    database would race on ``CREATE TABLE``. A session-scoped advisory lock makes the
    second worker wait, and its own ``migrate`` then finds nothing left to do.

    The unlock is best-effort. If the repair left the connection unusable the lock is
    released anyway when the session ends, so there is nothing to recover.
    """
    with connections[alias].cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(%s)", [ADVISORY_LOCK_KEY])
        try:
            yield
        finally:
            try:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [ADVISORY_LOCK_KEY])
            except DatabaseError:
                logger.debug("Advisory lock released by session teardown instead.")


def repair_missing_tables(alias: str = DEFAULT_DB_ALIAS) -> bool:
    """Create the revocation tables if they are missing. Returns whether they are usable.

    Called from ``wsgi.py``/``asgi.py`` on worker boot, before the first request. A worker
    that can sign users in but cannot revoke a stolen refresh token is the failure mode
    this project already paid for once, and a migration belongs in the deploy pipeline -
    but a deploy that reaches production without it should repair itself rather than lock
    every user out until someone notices.

    Scoped deliberately to the ``token_blacklist`` app: two tables, no schema-wide DDL, and
    nothing to do when the tables are already there. Every other migration stays the
    responsibility of ``build.sh``.
    """
    if not enabled() or getattr(settings, "IS_TESTING", False):
        return True

    missing = missing_tables(alias)
    if missing is None:
        # Unreachable database. Reported by crm.E001 / the readiness probe; blocking the
        # boot here would turn a recoverable database blip into a crash loop.
        return True
    if not missing:
        return True

    logger.warning(
        "token_blacklist tables missing (%s); applying that app's migrations at boot.",
        ", ".join(missing),
    )
    try:
        with _advisory_lock(alias):
            call_command("migrate", "token_blacklist", verbosity=0, interactive=False)
    except Exception as exc:  # noqa: BLE001 - a failed repair must not stop the worker
        logger.error(
            "Could not create the token_blacklist tables at boot (%s). Login still "
            "works, but sessions expire instead of being revoked.",
            exc,
        )

    still_missing = missing_tables(alias)
    if still_missing:
        logger.error(
            "%s still absent after migrating. Either the database user cannot run DDL "
            "or the migration needs attention; run `python manage.py migrate "
            "token_blacklist` against the service database.",
            ", ".join(still_missing),
        )
        return False

    logger.info("token_blacklist tables created; refresh-token revocation is active.")
    reset_cache()
    return True
