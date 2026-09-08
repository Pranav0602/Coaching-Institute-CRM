"""
Project-level Django system checks.

These run automatically on ``manage.py check``, ``manage.py migrate``, ``runserver``
startup, and can be used as a container readiness probe. They are registered from
``accounts.apps.AccountsConfig.ready()`` because ``institute_crm`` is the project
package rather than an installed app.

The intent is fail-fast, actionable configuration errors instead of a mystery failure
on the first query. When the ``rag`` app is added it should register its own
``rag.E00x`` checks in ``RagConfig.ready()`` and may reuse
:func:`postgres_extension_available` from here.

Error codes
-----------
``crm.E001``  Database engine is not PostgreSQL.
``crm.E002``  RAG is enabled but the ``vector`` extension is unavailable.
``crm.E003``  Insecure production configuration.
``crm.W001``  Media root is not writable.
``crm.W002``  RAG embedding dimension looks inconsistent with the selected model.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.checks import CheckMessage, Error, Tags, Warning as CheckWarning, register
from django.db import connections, OperationalError

logger = logging.getLogger("institute_crm.checks")

POSTGRES_ENGINE = "django.db.backends.postgresql"

# Known embedding dimensions, used only to catch obvious misconfiguration.
_KNOWN_EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "amazon.titan-embed-text-v1": 1536,
    "amazon.titan-embed-text-v2:0": 1024,
}


def postgres_extension_available(extension: str = "vector", alias: str = "default") -> bool | None:
    """Return True/False if the extension's availability could be determined, else None.

    ``None`` means the database could not be reached, which is a different problem and
    is reported separately so we don't emit a misleading "extension missing" error.
    """
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_available_extensions WHERE name = %s", [extension]
            )
            return cursor.fetchone() is not None
    except OperationalError:
        return None
    except Exception:  # pragma: no cover - defensive
        logger.warning("Could not probe for the %r extension.", extension, exc_info=True)
        return None


def postgres_extension_installed(extension: str = "vector", alias: str = "default") -> bool | None:
    """Whether the extension is actually created in the current database."""
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = %s", [extension])
            return cursor.fetchone() is not None
    except OperationalError:
        return None
    except Exception:  # pragma: no cover - defensive
        return None


@register(Tags.database)
def check_database_backend(app_configs, **kwargs) -> list[CheckMessage]:
    """The project supports PostgreSQL only.

    ``settings.py`` already refuses to import with a non-PostgreSQL ``DB_ENGINE``, so
    this is a second line of defence that also catches programmatic overrides such as
    a test settings module or a stray ``settings.DATABASES`` mutation.
    """
    engine = settings.DATABASES.get("default", {}).get("ENGINE")
    if engine == POSTGRES_ENGINE:
        return []
    return [
        Error(
            f"The default database engine is {engine!r}, but this project requires "
            f"{POSTGRES_ENGINE!r}.",
            hint=(
                "SQLite is not supported. The schema depends on PostgreSQL features and "
                "the RAG corpus requires the pgvector extension, which exists only for "
                "PostgreSQL. Start PostgreSQL (`docker compose up -d db`, or a local "
                "server) and set DB_* variables in .env. See SETUP.md."
            ),
            id="crm.E001",
        )
    ]


@register(Tags.database)
def check_pgvector_extension(app_configs, **kwargs) -> list[CheckMessage]:
    """When RAG is enabled outside tests, `vector` must be usable.

    Reported as an actionable configuration error rather than deferred to the first
    embedding query, per RAG_IMPLEMENTATION_PLAN.md 4.1.
    """
    if not getattr(settings, "RAG_ENABLED", False):
        return []
    if getattr(settings, "IS_TESTING", False):
        # Unit tests are expected to run against an in-memory fake repository.
        return []

    available = postgres_extension_available("vector")
    if available is None:
        return [
            CheckWarning(
                "Could not verify that the PostgreSQL `vector` extension is available "
                "because the database is unreachable.",
                hint=(
                    "This is not necessarily a RAG problem - confirm the database is "
                    "running and DB_HOST/DB_PORT/DB_USER/DB_PASSWORD are correct, then "
                    "re-run `manage.py check`."
                ),
                id="crm.W003",
            )
        ]
    if not available:
        return [
            Error(
                "RAG_ENABLED is true but the PostgreSQL `vector` extension is not "
                "available on this server.",
                hint=(
                    "pgvector must be installed server-side. Use the "
                    "`pgvector/pgvector:pg16` image, or install the extension package "
                    "for your PostgreSQL build, then run "
                    "`CREATE EXTENSION IF NOT EXISTS vector;` in the target database."
                ),
                id="crm.E002",
            )
        ]

    if postgres_extension_installed("vector") is False:
        return [
            CheckWarning(
                "The `vector` extension is available but has not been created in this "
                "database yet.",
                hint="Run: CREATE EXTENSION IF NOT EXISTS vector;",
                id="crm.W004",
            )
        ]
    return []


@register(Tags.security, deploy=True)
def check_production_configuration(app_configs, **kwargs) -> list[CheckMessage]:
    """Catch development-style defaults that must not reach a deployed environment."""
    messages: list[CheckMessage] = []

    if settings.DEBUG:
        return messages

    if "*" in settings.ALLOWED_HOSTS:
        messages.append(
            Error(
                "ALLOWED_HOSTS contains a wildcard while DEBUG is False.",
                hint="List the exact hostnames this service answers on.",
                id="crm.E003",
            )
        )
    if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
        messages.append(
            Error(
                "CORS_ALLOW_ALL_ORIGINS is enabled while DEBUG is False.",
                hint="Set CORS_ALLOWED_ORIGINS to the exact frontend origins instead.",
                id="crm.E003",
            )
        )
    return messages


@register()
def check_media_root_writable(app_configs, **kwargs) -> list[CheckMessage]:
    """Profile photos and documents are written here; surface permission issues early."""
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if not media_root:
        return []
    try:
        media_root.mkdir(parents=True, exist_ok=True)
        probe = media_root / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return [
            CheckWarning(
                f"MEDIA_ROOT ({media_root}) is not writable: {exc}",
                hint=(
                    "Uploads such as profile photos will fail. Fix the directory "
                    "permissions, point MEDIA_ROOT elsewhere, or enable "
                    "USE_S3_FOR_UPLOADS with valid AWS credentials."
                ),
                id="crm.W001",
            )
        ]
    return []


@register()
def check_rag_embedding_settings(app_configs, **kwargs) -> list[CheckMessage]:
    """A mismatched dimension silently corrupts a vector index, so flag it up front."""
    model = getattr(settings, "RAG_EMBEDDING_MODEL", "")
    dimensions = getattr(settings, "RAG_EMBEDDING_DIMENSIONS", None)
    expected = _KNOWN_EMBEDDING_DIMENSIONS.get(model)
    if expected is None or dimensions == expected:
        return []
    return [
        CheckWarning(
            f"RAG_EMBEDDING_DIMENSIONS is {dimensions} but {model!r} produces "
            f"{expected}-dimensional embeddings.",
            hint=(
                "The vector column width must match the embedding model exactly. "
                "Changing either after indexing requires a full re-index."
            ),
            id="crm.W002",
        )
    ]


def run_readiness_checks() -> list[str]:
    """Programmatic entrypoint for a deployment/health probe.

    Returns a list of human-readable blocking problems; empty means ready.
    """
    blocking: list[str] = []
    for check in (check_database_backend, check_pgvector_extension):
        for message in check(None):
            if isinstance(message, Error):
                blocking.append(f"{message.id}: {message.msg}")
    return blocking
