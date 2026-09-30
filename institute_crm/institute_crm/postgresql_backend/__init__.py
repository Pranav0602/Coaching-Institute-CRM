"""
PostgreSQL backend that survives a connection dying mid-request.

Why this exists
---------------
Each worker keeps its database connection open for ``CONN_MAX_AGE`` seconds (60 by
default, across two gunicorn workers x four threads). A managed database reached over
TLS can drop that connection while it sits idle: the next TLS record arrives
truncated or out of order, libpq aborts the stream, and psycopg2 raises::

    psycopg2.OperationalError: SSL error: decryption failed or bad record mac

That is not a malformed query, a bad password or a missing table - the SQL never
reached PostgreSQL. The socket died. The visible symptom is a 500 on whichever
request happens to be first after the drop, which in practice is *every*
authenticated request, because SimpleJWT loads the user before the view runs. So the
whole API 500s for the length of a 60-second connection window.

Django's own answer is ``CONN_HEALTH_CHECKS`` (enabled in settings.py): ping a reused
connection and replace it when the ping fails. That covers a connection that was
already dead when it was handed back, but not one that dies between the health check
and the statement, and not a TLS handshake that fails on a cold connect. This backend
closes both gaps by retrying the statement once on a fresh connection.

What is retried, and what is not
--------------------------------
A dead connection says nothing about whether PostgreSQL ran the statement, so a blind
retry could apply a write twice. The retry is therefore deliberately narrow:

* only ``OperationalError`` - never ``ProgrammingError``, ``IntegrityError`` and the
  rest, which are the database telling us something real;
* only when the failure identifies a dead or broken stream
  (:func:`~institute_crm.postgresql_backend.base.is_transient_failure`);
* only outside an atomic block, where a replay would join a transaction whose state
  is already unknown;
* only for statements that cannot change data
  (:func:`~institute_crm.postgresql_backend.base.is_replayable`).

A write that hits a dead socket still raises, so the request fails loudly instead of
silently duplicating a fee or a payment. Reads - the whole authentication path, and
every GET - are transparent. On top of that, ``CONN_HEALTH_CHECKS`` plus libpq
keepalives (see ``settings.py``) mean most dropped connections never get this far.

Configuration
-------------
``DB_RETRY_ON_BROKEN_CONNECTION=false``  disable the retry (stock behaviour)
``DB_RETRY_DELAY_SECONDS=0.2``            pause before reconnecting
``DB_MAX_RETRIES=1``                      attempts per statement (constant, not env)

The engine stays a PostgreSQL engine whichever way it is set, and ``DB_ENGINE`` may
also be left as ``django.db.backends.postgresql`` to run the unmodified backend.

Layout follows Django's backend convention: ``institute_crm.postgresql_backend.base``
holds the implementation (Django's ``load_backend`` imports exactly that module), and
this package re-exports the pieces the tests and settings refer to.
"""

from .base import (  # noqa: F401
    ENGINE,
    STOCK_ENGINE,
    DatabaseWrapper,
    RetryingCursor,
    RetryingDebugCursor,
    describe,
    is_replayable,
    is_transient_failure,
    retry_delay_seconds,
    retry_enabled,
    should_retry,
)
