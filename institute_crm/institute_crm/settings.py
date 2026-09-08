"""
Django settings for the Coaching Institute CRM.

Database policy
---------------
This project **requires PostgreSQL**. There is deliberately no SQLite fallback: the
platform is built around PostgreSQL-specific features (``pgvector`` for the planned RAG
corpus, JSONB, full-text search). A misconfigured engine fails loudly at import time
rather than silently degrading, because a partially-working vector index is worse than a
refusal to boot. See ``institute_crm/checks.py`` for the runtime system checks and
``RAG_IMPLEMENTATION_PLAN.md`` for the wider design.

Configuration is read from the environment. A ``.env`` file at the Django project root is
loaded automatically for local development; see ``.env.example`` for the full list.
"""
from pathlib import Path
from datetime import timedelta
import importlib.util
import os
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

from django.core.exceptions import ImproperlyConfigured  # noqa: E402


# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------
# Intentionally dependency-free so a fresh checkout boots without `pip install`.
# Real values belong in `.env` (git-ignored), never in this file.
def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Real environment variables always win over the file.
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")


def env_str(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(
            f"Missing required environment variable {name!r}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value or ""


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be an integer, got {raw!r}") from exc


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _detect_test_process() -> bool:
    """Narrow detection of a test runner, per RAG_IMPLEMENTATION_PLAN.md 4.1.

    Deliberately *not* a ``DEBUG`` heuristic. Only used to relax RAG-specific
    readiness requirements; it never relaxes the PostgreSQL requirement.
    """
    argv = " ".join(sys.argv)
    return (
        "pytest" in argv
        or "py.test" in argv
        or ("manage.py" in argv and " test" in f" {argv} ")
        or bool(os.environ.get("PYTEST_CURRENT_TEST"))
    )


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = env_bool("DEBUG", default=True)
IS_TESTING = env_bool("IS_TESTING", default=_detect_test_process())

# Dev convenience: an insecure key is tolerated with DEBUG on, and reported by
# `manage.py check`. With DEBUG off it is a hard error.
_INSECURE_SECRET_KEY = "django-insecure-local-development-key-do-not-use-in-production"
SECRET_KEY = env_str("DJANGO_SECRET_KEY", default="") or _INSECURE_SECRET_KEY
if not DEBUG and SECRET_KEY == _INSECURE_SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set to a unique secret value when DEBUG=False. "
        "Generate one with: python -c \"import secrets;print(secrets.token_urlsafe(64))\""
    )

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
if not DEBUG and ("*" in ALLOWED_HOSTS or not ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must list explicit hostnames when DEBUG=False; wildcards are not allowed."
    )

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third Party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",

    # Local Apps
    "accounts",
    "users_profiles",
    "crm_leads",
    "academics",
    "assignments_exams",
    "finance",
    "communications",
    "rag",
]

# drf_spectacular is optional; the API works without it.
HAS_SPECTACULAR = importlib.util.find_spec("drf_spectacular") is not None
if HAS_SPECTACULAR:
    INSTALLED_APPS.append("drf_spectacular")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "accounts.middleware.AuditLogMiddleware",
]

AUTH_USER_MODEL = "accounts.User"
ROOT_URLCONF = "institute_crm.urls"
WSGI_APPLICATION = "institute_crm.wsgi.application"
ASGI_APPLICATION = "institute_crm.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Database - PostgreSQL only, enforced
# ---------------------------------------------------------------------------
POSTGRES_ENGINE = "django.db.backends.postgresql"

DB_ENGINE = env_str("DB_ENGINE", default=POSTGRES_ENGINE)
if DB_ENGINE != POSTGRES_ENGINE:
    raise ImproperlyConfigured(
        f"This project requires PostgreSQL. DB_ENGINE was {DB_ENGINE!r}, expected "
        f"{POSTGRES_ENGINE!r}. SQLite and other backends are not supported: the schema "
        f"relies on PostgreSQL features and the planned RAG corpus requires the pgvector "
        f"extension. Start PostgreSQL (see SETUP.md or `docker compose up db`) instead of "
        f"changing this value."
    )

if importlib.util.find_spec("psycopg2") is None and importlib.util.find_spec("psycopg") is None:
    raise ImproperlyConfigured(
        "No PostgreSQL driver found. Install dependencies with: "
        "pip install -r requirements.txt"
    )

DATABASES = {
    "default": {
        "ENGINE": POSTGRES_ENGINE,
        "NAME": env_str("DB_NAME", "Institute_CRM"),
        "USER": env_str("DB_USER", "postgres"),
        "PASSWORD": env_str("DB_PASSWORD", required=True),
        "HOST": env_str("DB_HOST", "127.0.0.1"),
        "PORT": env_str("DB_PORT", "5432"),
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        "OPTIONS": {
            "connect_timeout": env_int("DB_CONNECT_TIMEOUT", 10),
        },
    }
}


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 480)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": True,
}


# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = env_str("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = env_str("MEDIA_URL", "/media/")
MEDIA_ROOT = Path(env_str("MEDIA_ROOT", str(BASE_DIR / "media")))

# Upload guardrails for user-supplied images (profile photos, documents).
MAX_UPLOAD_SIZE_BYTES = env_int("MAX_UPLOAD_SIZE_BYTES", 5 * 1024 * 1024)  # 5 MB
ALLOWED_IMAGE_EXTENSIONS = env_list("ALLOWED_IMAGE_EXTENSIONS", "jpg,jpeg,png,webp")

# When credentials are present, user uploads are mirrored to S3 and the object URL is
# stored alongside the local file. Absent credentials, local media is authoritative.
AWS_STORAGE_BUCKET_NAME = env_str("AWS_STORAGE_BUCKET_NAME", "")
AWS_REGION = env_str("AWS_REGION", "ap-south-1")
USE_S3_FOR_UPLOADS = env_bool("USE_S3_FOR_UPLOADS", default=bool(AWS_STORAGE_BUCKET_NAME))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
)
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", default=False)
CORS_ALLOW_CREDENTIALS = True
if not DEBUG and CORS_ALLOW_ALL_ORIGINS:
    raise ImproperlyConfigured(
        "CORS_ALLOW_ALL_ORIGINS cannot be enabled when DEBUG=False. "
        "List explicit origins in CORS_ALLOWED_ORIGINS instead."
    )


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "institute_crm.renderers.StandardResponseRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "EXCEPTION_HANDLER": "institute_crm.renderers.custom_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "anon": env_str("THROTTLE_ANON", "60/min"),
        "user": env_str("THROTTLE_USER", "1000/hour"),
        # Reserved for the future public assistant endpoint.
        "assistant_anon": env_str("THROTTLE_ASSISTANT_ANON", "10/min"),
        "assistant_user": env_str("THROTTLE_ASSISTANT_USER", "60/min"),
    },
}

if HAS_SPECTACULAR:
    REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"
    SPECTACULAR_SETTINGS = {
        "TITLE": "Coaching Institute CRM & ERP API",
        "DESCRIPTION": (
            "Multi-branch coaching institute CRM backend: RBAC via JWT, AWS-backed "
            "notifications and storage, PostgreSQL persistence."
        ),
        "VERSION": "1.0.0",
        "SERVE_INCLUDE_SCHEMA": False,
    }


# ---------------------------------------------------------------------------
# RAG platform flags (Phase 1 groundwork only - see RAG_IMPLEMENTATION_PLAN.md)
# ---------------------------------------------------------------------------
# The `rag` app does not exist yet. These flags exist so that the database and
# readiness checks, deployment manifests, and env templates are already correct when
# it lands, and so that nothing can enable a half-configured vector pipeline.
RAG_ENABLED = env_bool("RAG_ENABLED", default=False)
RAG_VECTOR_REPOSITORY = "fake" if IS_TESTING else env_str("RAG_VECTOR_REPOSITORY", "pgvector")
RAG_EMBEDDING_MODEL = env_str("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
RAG_EMBEDDING_DIMENSIONS = env_int("RAG_EMBEDDING_DIMENSIONS", 1536)


# ---------------------------------------------------------------------------
# Security headers (applied when running without DEBUG)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    X_FRAME_OPTIONS = "DENY"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# The codebase logs under the `institute_crm.*` namespace (per-app children such as
# `institute_crm.finance`). Without this config those records were discarded.
LOG_LEVEL = env_str("LOG_LEVEL", "INFO" if not DEBUG else "DEBUG")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname:<8} {name} {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.db.backends": {
            "handlers": ["console"],
            "level": env_str("SQL_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
        "institute_crm": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}
