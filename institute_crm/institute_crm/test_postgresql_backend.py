"""
Tests for :mod:`institute_crm.postgresql_backend`.

These are the rules that decide whether a request is replayed after a database
connection dies, so they are asserted directly rather than through a live server:
``SimpleTestCase`` keeps them out of the database-backed suite, and a fake cursor
makes the broken-connection path reproducible on demand instead of only in
production.

The failures being guarded against are real ones from a deployed worker::

    psycopg2.OperationalError: SSL error: decryption failed or bad record mac
"""

import os
import unittest
from unittest import mock

from django.db import DatabaseError, IntegrityError, OperationalError, ProgrammingError
from django.test import SimpleTestCase

from institute_crm.postgresql_backend import base as backend


class FakeRawCursor:
    """A psycopg2-shaped cursor that can be told to fail its first ``n`` calls."""

    def __init__(self, failures: int = 0, error: Exception | None = None):
        self.failures = failures
        self.error = error or OperationalError("SSL error: decryption failed or bad record mac")
        self.executed: list[tuple[str, object]] = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if self.failures:
            self.failures -= 1
            raise self.error
        return "ok"

    def executemany(self, sql, param_list):
        self.executed.append((sql, param_list))
        if self.failures:
            self.failures -= 1
            raise self.error
        return "ok"

    def fetchone(self):
        return (1,)


class FakeConnection:
    """Enough of ``DatabaseWrapper`` for ``CursorWrapper`` to run against it."""

    def __init__(
        self,
        raw_cursor: FakeRawCursor,
        *,
        in_atomic_block: bool = False,
        fresh_failures: int = 0,
    ):
        self.connection = mock.Mock()
        self.connection.cursor.return_value = raw_cursor
        self.raw_cursor = raw_cursor
        self.in_atomic_block = in_atomic_block
        self.fresh_failures = fresh_failures
        self.errors_occurred = False
        self.execute_wrappers: list = []
        self.closed = 0
        self.reconnects = 0

    # -- DatabaseWrapper surface used by CursorWrapper / reconnect ---------------
    def validate_no_broken_transaction(self):
        return None

    @property
    def wrap_database_errors(self):
        return _PassthroughErrors()

    def close(self):
        self.closed += 1
        self.connection = None

    def ensure_connection(self):
        self.reconnects += 1
        fresh = FakeRawCursor(failures=self.fresh_failures)
        self.connection = mock.Mock()
        self.connection.cursor.return_value = fresh
        self.raw_cursor = fresh


class _PassthroughErrors:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class TransientFailureDetectionTests(SimpleTestCase):
    def test_reports_the_production_ssl_failure_as_transient(self):
        exc = OperationalError("SSL error: decryption failed or bad record mac")
        self.assertTrue(backend.is_transient_failure(exc))

    def test_recognises_a_connection_dropped_while_idle(self):
        for message in (
            "server closed the connection unexpectedly",
            "terminating connection due to administrator command",
            "consuming input failed",
            "connection reset by peer",
            "SSL error: bad record mac",
            "connection timeout expired",
        ):
            with self.subTest(message=message):
                self.assertTrue(backend.is_transient_failure(OperationalError(message)))

    def test_looks_through_the_django_wrapped_driver_exception(self):
        cause = OperationalError("could not receive data from server")
        wrapped = OperationalError("SSL error")
        wrapped.__cause__ = cause
        self.assertTrue(backend.is_transient_failure(wrapped))

    def test_does_not_treat_a_real_database_error_as_transient(self):
        for message in (
            'relation "accounts_user" does not exist',
            "column notification.user_id does not exist",
            "permission denied for table accounts_user",
            "canceling statement due to statement timeout",
            "deadlock detected",
        ):
            with self.subTest(message=message):
                self.assertFalse(backend.is_transient_failure(OperationalError(message)))

    def test_survives_an_exception_cycle(self):
        first = OperationalError("SSL error")
        second = OperationalError("SSL error")
        first.__cause__ = second
        second.__cause__ = first
        self.assertTrue(backend.is_transient_failure(first))


class ReplayableStatementTests(SimpleTestCase):
    def test_reads_are_replayable(self):
        for sql in (
            "SELECT 1",
            "SELECT id FROM accounts_user WHERE id = %s",
            "  -- fetched by the auth middleware\nSELECT id FROM accounts_user",
            "/* jwt lookup */ SELECT id FROM accounts_user",
            "SELECT notification_id FROM communications_notification FOR UPDATE",
            "SHOW search_path",
            "EXPLAIN SELECT 1",
            "SET timezone = 'UTC'",
        ):
            with self.subTest(sql=sql):
                self.assertTrue(backend.is_replayable(sql))

    def test_writes_are_not_replayable(self):
        for sql in (
            "INSERT INTO finance_invoice (total) VALUES (10)",
            "UPDATE accounts_user SET last_login = now()",
            "DELETE FROM communications_notification",
            "TRUNCATE finance_invoice",
            "CREATE TABLE t (id int)",
            "SAVEPOINT s1",
            # A CTE that ends in a write is a write, even though it starts with WITH.
            "WITH rows AS (SELECT 1) INSERT INTO finance_invoice SELECT * FROM rows",
            # `SELECT ... INTO` creates a table.
            "SELECT id INTO archived_user FROM accounts_user",
            "",
            "   ",
        ):
            with self.subTest(sql=sql):
                self.assertFalse(backend.is_replayable(sql))


class ShouldRetryTests(SimpleTestCase):
    def setUp(self):
        self.connection = FakeConnection(FakeRawCursor())
        self.transient = OperationalError("SSL error: decryption failed or bad record mac")

    def test_retries_a_read_after_a_dead_connection(self):
        self.assertTrue(backend.should_retry(self.connection, "SELECT 1", self.transient))

    def test_does_not_retry_inside_an_atomic_block(self):
        self.connection.in_atomic_block = True
        self.assertFalse(backend.should_retry(self.connection, "SELECT 1", self.transient))

    def test_does_not_retry_a_write(self):
        self.assertFalse(
            backend.should_retry(self.connection, "UPDATE accounts_user SET x = 1", self.transient)
        )

    def test_does_not_retry_an_error_the_database_intended(self):
        self.assertFalse(
            backend.should_retry(
                self.connection, "SELECT 1", OperationalError('relation "t" does not exist')
            )
        )

    def test_does_not_retry_a_non_operational_error(self):
        self.assertFalse(
            backend.should_retry(
                self.connection, "SELECT 1", ProgrammingError("syntax error at or near SELCT")
            )
        )
        self.assertFalse(
            backend.should_retry(
                self.connection,
                "SELECT 1",
                IntegrityError('duplicate key value violates unique constraint "x_user_id_key"'),
            )
        )

    def test_does_not_retry_when_disabled_by_environment(self):
        with mock.patch.dict(os.environ, {"DB_RETRY_ON_BROKEN_CONNECTION": "false"}):
            self.assertFalse(backend.should_retry(self.connection, "SELECT 1", self.transient))
        with mock.patch.dict(os.environ, {"DB_RETRY_ON_BROKEN_CONNECTION": "off"}):
            self.assertFalse(backend.should_retry(self.connection, "SELECT 1", self.transient))
        with mock.patch.dict(os.environ, {"DB_RETRY_ON_BROKEN_CONNECTION": "1"}):
            self.assertTrue(backend.should_retry(self.connection, "SELECT 1", self.transient))


class CursorRetryTests(SimpleTestCase):
    def setUp(self):
        # The reconnect pause exists for a provider restarting its endpoint; there is
        # nothing to wait for in these tests.
        patcher = mock.patch.dict(os.environ, {"DB_RETRY_DELAY_SECONDS": "0"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_read_survives_a_connection_that_dies_first_time(self):
        connection = FakeConnection(FakeRawCursor(failures=1))
        cursor = backend.RetryingCursor(connection.raw_cursor, connection)

        self.assertEqual("ok", cursor.execute("SELECT 1", [1]))

        self.assertEqual(1, connection.closed, "the broken connection should be discarded")
        self.assertEqual(1, connection.reconnects, "exactly one reconnect")
        self.assertEqual(1, len(connection.raw_cursor.executed))
        self.assertEqual("SELECT 1", connection.raw_cursor.executed[0][0])
        self.assertEqual([1], connection.raw_cursor.executed[0][1], "params must be replayed")

    def test_the_second_failure_is_reported_to_the_caller(self):
        # The replacement connection is dropped as well: that is a real outage, and
        # the request must fail with it rather than retry forever.
        connection = FakeConnection(FakeRawCursor(failures=1), fresh_failures=1)
        cursor = backend.RetryingCursor(connection.raw_cursor, connection)

        with self.assertRaises(OperationalError):
            cursor.execute("SELECT 1")

        self.assertEqual(1, connection.reconnects, "the retry happens once, not in a loop")

    def test_a_write_that_hits_a_dead_connection_is_never_replayed(self):
        connection = FakeConnection(FakeRawCursor(failures=1))
        cursor = backend.RetryingCursor(connection.raw_cursor, connection)

        with self.assertRaises(OperationalError):
            cursor.execute("INSERT INTO finance_invoice (total) VALUES (10)")

        self.assertEqual(0, connection.reconnects)
        self.assertEqual(0, connection.closed)

    def test_a_healthy_connection_is_left_alone(self):
        connection = FakeConnection(FakeRawCursor())
        cursor = backend.RetryingCursor(connection.raw_cursor, connection)

        self.assertEqual("ok", cursor.execute("SELECT 1"))
        self.assertEqual(0, connection.reconnects)
        self.assertEqual(0, connection.closed)

    def test_a_successful_retry_clears_the_error_flag_for_the_new_connection(self):
        connection = FakeConnection(FakeRawCursor(failures=1))
        connection.errors_occurred = True
        cursor = backend.RetryingCursor(connection.raw_cursor, connection)

        cursor.execute("SELECT 1")

        self.assertFalse(connection.errors_occurred)

    def test_batch_reads_are_retried_too(self):
        connection = FakeConnection(FakeRawCursor(failures=1))
        cursor = backend.RetryingCursor(connection.raw_cursor, connection)

        self.assertEqual("ok", cursor.executemany("SELECT id FROM accounts_user", [[1], [2]]))
        self.assertEqual(1, connection.reconnects)

    def test_closing_a_broken_connection_never_masks_the_retry(self):
        connection = FakeConnection(FakeRawCursor(failures=1))
        connection.close = mock.Mock(side_effect=DatabaseError("connection not open"))
        cursor = backend.RetryingCursor(connection.raw_cursor, connection)

        self.assertEqual("ok", cursor.execute("SELECT 1"))
        self.assertEqual(1, connection.reconnects)


class ConnectRetryTests(SimpleTestCase):
    # A real DatabaseWrapper is used here with `connect` stubbed out. The wrapper is
    # never allowed to open a connection, but Django patches `ensure_connection` in
    # SimpleTestCase to refuse database access, so it has to be declared anyway.
    databases = {"default"}

    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"DB_RETRY_DELAY_SECONDS": "0"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _wrapper(self, connect_effects):
        """A real DatabaseWrapper with ``connect`` stubbed, so no server is contacted."""
        wrapper = backend.DatabaseWrapper(
            {"ENGINE": backend.ENGINE, "NAME": "unused", "OPTIONS": {}}, "default"
        )
        wrapper.connect = mock.Mock(side_effect=connect_effects)
        return wrapper

    def test_a_connect_that_dies_transiently_is_retried(self):
        transient = OperationalError("SSL error: decryption failed or bad record mac")
        wrapper = self._wrapper([transient, None])

        wrapper.ensure_connection()

        self.assertEqual(2, wrapper.connect.call_count)

    def test_a_refused_connection_is_not_retried(self):
        # One refusal is not a broken connection: retrying it would only add a
        # connection attempt to a genuine outage.
        refused = OperationalError("could not connect to server: Connection refused")
        wrapper = self._wrapper([refused, None])

        with self.assertRaises(OperationalError):
            wrapper.ensure_connection()

        self.assertEqual(1, wrapper.connect.call_count)

    def test_a_retryable_error_with_no_second_attempt_left_still_raises(self):
        transient = OperationalError("SSL error: decryption failed or bad record mac")
        wrapper = self._wrapper([transient, transient])

        with self.assertRaises(OperationalError):
            wrapper.ensure_connection()

        self.assertEqual(2, wrapper.connect.call_count)

    def test_disabling_the_retry_keeps_the_stock_single_attempt(self):
        transient = OperationalError("SSL error: decryption failed or bad record mac")
        wrapper = self._wrapper([transient, None])
        with mock.patch.dict(os.environ, {"DB_RETRY_ON_BROKEN_CONNECTION": "false"}):
            with self.assertRaises(OperationalError):
                wrapper.ensure_connection()
        self.assertEqual(1, wrapper.connect.call_count)


class EngineWiringTests(SimpleTestCase):
    def test_django_can_load_the_engine(self):
        # Django's load_backend imports "<ENGINE>.base", so the implementation has to
        # live in a package rather than a single module.
        from django.db.utils import load_backend

        self.assertIs(load_backend(backend.ENGINE), backend)

    def test_describe_reports_the_active_configuration(self):
        with mock.patch.dict(os.environ, {"DB_RETRY_ON_BROKEN_CONNECTION": "false"}):
            described = backend.describe()
        self.assertEqual(backend.ENGINE, described["engine"])
        self.assertFalse(described["retry_enabled"])
        self.assertEqual(backend.MAX_RETRIES, described["max_retries"])

    def test_cursors_are_the_retrying_kinds(self):
        wrapper = backend.DatabaseWrapper(
            {"ENGINE": backend.ENGINE, "NAME": "unused", "OPTIONS": {}}, "default"
        )
        self.assertIsInstance(wrapper.make_cursor(None), backend.RetryingCursor)
        self.assertIsInstance(wrapper.make_debug_cursor(None), backend.RetryingDebugCursor)

    def test_settings_actually_select_this_engine(self):
        from django.conf import settings

        self.assertIn(
            settings.DATABASES["default"]["ENGINE"],
            {backend.ENGINE, backend.STOCK_ENGINE},
        )
        self.assertTrue(
            settings.DATABASES["default"].get("CONN_HEALTH_CHECKS"),
            "reused connections must be health-checked, or a dropped connection is "
            "handed straight to a request",
        )
        options = settings.DATABASES["default"].get("OPTIONS", {})
        self.assertTrue(options.get("keepalives"), "TCP keepalives should be enabled")

    def test_the_engine_check_accepts_both_postgres_backends(self):
        from django.conf import settings

        from institute_crm import checks

        default = settings.DATABASES["default"]
        try:
            for engine in (backend.ENGINE, backend.STOCK_ENGINE, "django.db.backends.sqlite3"):
                with self.subTest(engine=engine):
                    settings.DATABASES["default"] = {"ENGINE": engine}
                    expected = [] if engine != "django.db.backends.sqlite3" else ["crm.E001"]
                    self.assertEqual(
                        expected, [m.id for m in checks.check_database_backend(None)]
                    )
        finally:
            settings.DATABASES["default"] = default


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
