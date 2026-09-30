"""
Implementation of the reconnecting PostgreSQL backend.

See the package docstring (``institute_crm.postgresql_backend``) for why this exists
and exactly which failures are retried. Django's ``load_backend`` imports this module
directly as the engine's ``base``, so nothing here may import from the package it
lives in.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

from django.db import DatabaseError, OperationalError
from django.db.backends.postgresql import base as postgresql
from django.db.backends.utils import CursorDebugWrapper, CursorWrapper

logger = logging.getLogger("institute_crm.db")

#: The engine path ``settings.py`` points ``DATABASES["default"]["ENGINE"]`` at.
ENGINE = "institute_crm.postgresql_backend"

#: Unmodified Django engine. Accepted wherever :data:`ENGINE` is, so a deployment can
#: fall back to it without touching ``DB_ENGINE``.
STOCK_ENGINE = "django.db.backends.postgresql"

#: One retry, not a loop: a second failure means the database is genuinely down, and
#: the request should surface that instead of spending the request timeout on it.
MAX_RETRIES = 1


def retry_enabled() -> bool:
    """``DB_RETRY_ON_BROKEN_CONNECTION`` - the escape hatch for the whole behaviour.

    Read at use time rather than cached in a module global: it is consulted on the
    failure path (and once per ``ensure_connection``), so the cost is nothing next to
    a database round trip, and a setting change in a running worker is picked up
    without having to hunt for the attribute to patch.
    """
    raw = os.environ.get("DB_RETRY_ON_BROKEN_CONNECTION")
    if raw is None or not raw.strip():
        return True
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def retry_delay_seconds() -> float:
    """``DB_RETRY_DELAY_SECONDS`` - pause before reconnecting.

    Long enough that a provider restarting its endpoint has a moment to accept new
    connections, short enough to stay well inside the gunicorn timeout on the login
    path.
    """
    raw = os.environ.get("DB_RETRY_DELAY_SECONDS")
    if raw is None or not raw.strip():
        return 0.2
    try:
        return max(0.0, float(raw))
    except ValueError:
        logger.warning("Ignoring DB_RETRY_DELAY_SECONDS=%r: not a number.", raw)
        return 0.2


#: libpq/psycopg2 messages that mean "this connection is gone", as opposed to the
#: database rejecting the statement. Matched case-insensitively against the whole
#: exception chain, because the wording differs by driver version and by whether the
#: failure happened during connect, query, or fetch.
_TRANSIENT_MARKERS = (
    "ssl error",
    "record mac",
    "decryption failed",
    "server closed the connection unexpectedly",
    "terminating connection",
    "connection not open",
    "connection already closed",
    "could not receive data from server",
    "consuming input failed",
    "connection reset by peer",
    "broken pipe",
    "no connection to the server",
    "eof detected",
    "server closed the connection",
    "connection timeout expired",
    "lost connection",
)

#: Leading keywords that cannot change data: the statement reads, or adjusts session
#: state, and nothing else. Deliberately an allowlist of single keywords rather than a
#: denylist of write keywords, because the failure mode of getting it wrong is a
#: duplicated write. ``WITH`` is not on it: a data-modifying CTE
#: (``WITH rows AS (...) INSERT INTO ...``) is a write that reads like a select, and
#: ``sqlparse`` disagrees with itself about which one it is.
_READ_ONLY_STATEMENT = re.compile(
    r"^\s*(?:select|show|explain|set|reset|discard|values|table)\b", re.IGNORECASE
)

#: ``SELECT ... INTO new_table`` creates a table in PostgreSQL, so it is a write
#: wearing a read's leading keyword. Column names such as ``into_score`` do not match
#: (underscore is a word character); the occasional false positive only costs a retry.
_SELECT_INTO_TABLE = re.compile(r"\binto\b", re.IGNORECASE)

#: Whitespace and comments before the first real token, which must not hide the
#: statement's leading keyword.
_LEADING_SQL_NOISE = re.compile(r"\A(?:\s+|--[^\n]*(?:\n|\Z)|/\*.*?\*/)*", re.DOTALL)


def is_transient_failure(exc: BaseException) -> bool:
    """Whether ``exc`` describes a connection that is gone, not a query that failed.

    Walks the ``__cause__``/``__context__`` chain because Django re-raises the driver's
    exception as ``django.db.utils.OperationalError`` with the original attached, and
    the wording that matters may sit on either one.
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        message = str(current).lower()
        if any(marker in message for marker in _TRANSIENT_MARKERS):
            return True
        current = current.__cause__ or current.__context__
    return False


def is_replayable(sql: str) -> bool:
    """Whether running ``sql`` again could change stored data. Conservative by design."""
    if not sql or not sql.strip():
        return False
    statement = _LEADING_SQL_NOISE.sub("", sql, count=1)
    if not _READ_ONLY_STATEMENT.match(statement):
        return False
    # `SELECT ... FOR UPDATE` takes a lock but writes nothing, so it stays replayable;
    # `SELECT ... INTO other_table` creates that table, so it does not.
    if _SELECT_INTO_TABLE.search(statement):
        return False
    return True


def should_retry(connection, sql: str, exc: BaseException) -> bool:
    """The single decision point for the retry, so the rules live in one testable place."""
    if MAX_RETRIES < 1 or not retry_enabled():
        return False
    if not isinstance(exc, OperationalError):
        return False
    if getattr(connection, "in_atomic_block", False):
        # The transaction this statement belonged to is already in an unknown state;
        # replaying it here would run against a different connection than the one the
        # surrounding atomic block is holding.
        return False
    if not is_transient_failure(exc):
        return False
    return is_replayable(sql)


def _discard_connection(connection) -> None:
    """Drop a connection we know is broken, ignoring errors raised while closing it."""
    try:
        connection.close()
    except DatabaseError:
        logger.debug("Closing a broken connection failed; discarding it anyway.", exc_info=True)
        connection.connection = None


def reconnect(connection):
    """Replace a dead connection and return a cursor on the fresh one."""
    delay = retry_delay_seconds()
    if delay:
        time.sleep(delay)
    _discard_connection(connection)
    connection.ensure_connection()
    return connection.connection.cursor()


class _RetryOnBrokenConnection:
    """Mixin that replays a read once, on a new connection, after a dead socket."""

    def _execute(self, sql, params, *ignored_wrapper_args):
        try:
            return super()._execute(sql, params, *ignored_wrapper_args)
        except OperationalError as exc:
            if not should_retry(self.db, sql, exc):
                raise
            logger.warning(
                "Database connection failed mid-statement (%s). Reconnecting and retrying the "
                "read once; a second failure is reported to the caller.",
                exc,
            )
            self.cursor = reconnect(self.db)
            result = super()._execute(sql, params, *ignored_wrapper_args)
            # The statement succeeded on a healthy connection, so an error recorded
            # against the discarded one would only get the fresh connection thrown
            # away at the end of the request.
            self.db.errors_occurred = False
            return result

    def _executemany(self, sql, param_list, *ignored_wrapper_args):
        try:
            return super()._executemany(sql, param_list, *ignored_wrapper_args)
        except OperationalError as exc:
            if not should_retry(self.db, sql, exc):
                raise
            logger.warning(
                "Database connection failed during a batch statement (%s). Reconnecting and "
                "retrying the batch read once.",
                exc,
            )
            self.cursor = reconnect(self.db)
            result = super()._executemany(sql, param_list, *ignored_wrapper_args)
            self.db.errors_occurred = False
            return result


class RetryingCursor(_RetryOnBrokenConnection, CursorWrapper):
    """Non-debug cursor: the one production requests use."""


class RetryingDebugCursor(_RetryOnBrokenConnection, CursorDebugWrapper):
    """Debug cursor, so ``connection.queries`` keeps working with the retry."""


class DatabaseWrapper(postgresql.DatabaseWrapper):
    """Stock psycopg2 backend plus the reconnect behaviour documented in the package.

    Everything else - connection parameters, schema editor, pgvector support, error
    translation - is inherited unchanged, which is why this is a subclass rather than a
    middleware or a retry helper sprinkled over call sites.
    """

    def make_cursor(self, cursor):
        return RetryingCursor(cursor, self)

    def make_debug_cursor(self, cursor):
        return RetryingDebugCursor(cursor, self)

    def ensure_connection(self):
        """Retry a failed connect, which covers a TLS handshake that dies on arrival.

        A cold worker whose first connection is dropped mid-handshake raises from
        ``connect()``, before any cursor exists, so the cursor-level retry never runs.
        """
        if not retry_enabled():
            return super().ensure_connection()
        try:
            return super().ensure_connection()
        except OperationalError as exc:
            if not is_transient_failure(exc):
                raise
            logger.warning("Database connect failed transiently (%s); retrying once.", exc)
            _discard_connection(self)
            return super().ensure_connection()


def describe() -> dict[str, Any]:
    """Introspection for diagnostics (health endpoints, shell debugging)."""
    return {
        "engine": ENGINE,
        "retry_enabled": retry_enabled(),
        "retry_delay_seconds": retry_delay_seconds(),
        "max_retries": MAX_RETRIES,
    }
