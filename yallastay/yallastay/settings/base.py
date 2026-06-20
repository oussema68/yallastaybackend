"""
Django base settings. Shared by dev and prod.
Based on BoilerPlate patterns.
"""

from pathlib import Path
from datetime import timedelta
import sys

from .env_util import env_bool, env_int, env_str

# Project root: folder containing manage.py (parent of yallastay config package)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env
try:
    from dotenv import load_dotenv

    project_root = BASE_DIR
    for p in [project_root / ".env", BASE_DIR.parent / ".env"]:
        if p.exists():
            load_dotenv(p, override=True)
            break
except ImportError:
    pass

TESTING = "test" in sys.argv or "pytest" in sys.modules


def _use_s3_media() -> bool:
    """
    Use S3-compatible object storage for user uploads (not PostgreSQL blobs).

    Set AWS_STORAGE_BUCKET_NAME (+ credentials). Tests always use local disk.
    USE_S3_MEDIA=false forces filesystem even if bucket name is present.
    """
    if TESTING:
        return False
    if (env_str("USE_S3_MEDIA") or "").lower() in ("0", "false", "no"):
        return False
    return bool(env_str("AWS_STORAGE_BUCKET_NAME"))


# Dev-only: `manage.py dev_reset_esign_session` - never enable in production.
ESIGN_DEV_RESET_ENABLED = False

# PostgreSQL Row Level Security: set app.request_user_id per request (see core/middleware/postgres_rls.py).
# Disable with POSTGRES_RLS_ENABLED=false if policies must be bypassed during incidents.
_POSTGRES_RLS_RAW = (env_str("POSTGRES_RLS_ENABLED") or "true").lower()
POSTGRES_RLS_ENABLED = _POSTGRES_RLS_RAW in ("1", "true", "yes", "on")

# Security - SECRET_KEY must come only from the environment / .env (never hardcoded here).
SECRET_KEY = env_str("SECRET_KEY")
if not SECRET_KEY:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "SECRET_KEY is required. Set it in the environment or yallastay/.env "
        '(copy .env.example). Generate: python -c "import secrets; print(secrets.token_urlsafe(40))"'
    )

DEBUG = True
ALLOWED_HOSTS = []

# Application definition
AUTH_USER_MODEL = "accounts.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "core",
    "accounts",
    "listings",
    "bookings",
    "reviews",
    "payments",
    "messaging",
    "lifestyle_services",
    "notifications",
    "analytics",
    "reports",
    "roommates",
    "documents",
    "sms",
    "emails",
    "esign",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.postgres_rls.PostgresRLSContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "yallastay.urls"
WSGI_APPLICATION = "yallastay.wsgi.application"

# JWT (override via environment)
_JWT_ACCESS_MINUTES = env_int(
    "JWT_ACCESS_TOKEN_LIFETIME_MINUTES", 30, min_value=1, max_value=24 * 60
)
_JWT_REFRESH_DAYS = env_int(
    "JWT_REFRESH_TOKEN_LIFETIME_DAYS", 1, min_value=1, max_value=365
)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=_JWT_ACCESS_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=_JWT_REFRESH_DAYS),
}


def _auth_throttle_rate(env_key: str, default_prod: str) -> str:
    """Tighter limits on auth endpoints; env overrides; very high caps in tests."""
    v = env_str(env_key)
    if v:
        return v
    if TESTING:
        return "10000/minute"
    return default_prod


# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env_str("API_THROTTLE_ANON")
        or ("1000/minute" if TESTING else "100/minute"),
        "user": env_str("API_THROTTLE_USER")
        or ("10000/day" if TESTING else "1000/day"),
        # ScopedRateThrottle on /api/auth/*: stricter than global anon/user
        "auth_login": _auth_throttle_rate("API_THROTTLE_AUTH_LOGIN", "5/minute"),
        "auth_register": _auth_throttle_rate("API_THROTTLE_AUTH_REGISTER", "5/minute"),
        "auth_refresh": _auth_throttle_rate("API_THROTTLE_AUTH_REFRESH", "30/minute"),
        "auth_password_reset": _auth_throttle_rate(
            "API_THROTTLE_AUTH_PASSWORD_RESET", "5/hour"
        ),
        "auth_password_reset_confirm": _auth_throttle_rate(
            "API_THROTTLE_AUTH_PASSWORD_RESET_CONFIRM", "10/minute"
        ),
        "auth_verify_email": _auth_throttle_rate(
            "API_THROTTLE_AUTH_VERIFY_EMAIL", "60/minute"
        ),
        "auth_resend_verification": _auth_throttle_rate(
            "API_THROTTLE_AUTH_RESEND_VERIFICATION", "5/hour"
        ),
        "payment_initiate": "120/minute" if TESTING else "30/minute",
        "stub_webhook": "600/minute" if TESTING else "30/minute",
    },
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"] if (BASE_DIR / "templates").exists() else [],
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

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Auth
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = env_str("LANGUAGE_CODE") or "en-us"
TIME_ZONE = env_str("TIME_ZONE") or "Asia/Dubai"
USE_I18N = True
USE_TZ = True

# Static & Media
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# User uploads: local ``media/`` by default; S3 when AWS_STORAGE_BUCKET_NAME is set.
# The database stores paths/keys only; never raw file bytes in PostgreSQL.
if _use_s3_media():
    _ak = env_str("AWS_ACCESS_KEY_ID")
    _sk = env_str("AWS_SECRET_ACCESS_KEY")
    if _ak:
        AWS_ACCESS_KEY_ID = _ak
    if _sk:
        AWS_SECRET_ACCESS_KEY = _sk
    AWS_STORAGE_BUCKET_NAME = env_str("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env_str("AWS_S3_REGION_NAME") or "me-central-1"
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_S3_FILE_OVERWRITE = False
    _s3_domain = env_str("AWS_S3_CUSTOM_DOMAIN")
    if _s3_domain:
        AWS_S3_CUSTOM_DOMAIN = _s3_domain
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

# URLs (for email links, etc.) — dev/prod modules set required values from .env
FRONTEND_URL = env_str("FRONTEND_URL")
BACKEND_URL = env_str("BACKEND_URL")

# Email (transactional - see ``emails`` app)
DEFAULT_FROM_EMAIL = env_str("DEFAULT_FROM_EMAIL") or "noreply@yallastay.local"
SERVER_EMAIL = DEFAULT_FROM_EMAIL
# In-app messages from "Yallastay Team" (must not be a real signup email)
YALLASTAY_TEAM_USER_EMAIL = env_str("YALLASTAY_TEAM_USER_EMAIL") or (
    "yallastay-team@internal.yallastay"
)
EMAIL_BACKEND = env_str("EMAIL_BACKEND") or (
    "django.core.mail.backends.console.EmailBackend"
)
# SMTP (production: Resend — see docs/RESEND_SETUP.md and .env.example)
EMAIL_HOST = env_str("EMAIL_HOST")
EMAIL_PORT = env_int("EMAIL_PORT", 587, min_value=1, max_value=65535)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_HOST_USER = env_str("EMAIL_HOST_USER") or "resend"
# RESEND_API_KEY is an alias for EMAIL_HOST_PASSWORD (Resend SMTP password = API key).
EMAIL_HOST_PASSWORD = env_str("EMAIL_HOST_PASSWORD") or env_str("RESEND_API_KEY")

# Internal verification team inbox (document checklist notifications)
VERIFICATION_TEAM_EMAIL = env_str("VERIFICATION_TEAM_EMAIL")

# Payments: "stub" (local/dev fake checkout) vs "stripe" (real Checkout Sessions)
# Use stub while developing app flows; switch to stripe + test keys for provider integration.
PAYMENT_PROVIDER = (env_str("PAYMENT_PROVIDER") or "stub").lower()
STRIPE_SECRET_KEY = env_str("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = env_str("STRIPE_WEBHOOK_SECRET")
STRIPE_PUBLISHABLE_KEY = env_str("STRIPE_PUBLISHABLE_KEY")

# Stub checkout (PAYMENT_PROVIDER=stub): client token prefix (configure in .env; not a live provider secret).
STUB_CHECKOUT_CLIENT_TOKEN_PREFIX = env_str("STUB_CHECKOUT_CLIENT_TOKEN_PREFIX") or (
    "stub_checkout_token"
)
# Optional shared secret for POST /api/payments/webhook/stub/ when not using JWT (curl, CI).
# In production (DEBUG=False), configure this or rely on JWT as the payment owner.
STUB_WEBHOOK_SECRET = env_str("STUB_WEBHOOK_SECRET")

# E-sign: auto-generate a placeholder lease PDF on payment (dev). Production relies on lister/realtor upload.
ESIGN_AUTO_GENERATE_CONTRACT_PDF = env_bool("ESIGN_AUTO_GENERATE_CONTRACT_PDF", False)

# E-sign uploads & signature image limits (tune via environment; no secrets)
ESIGN_LEASE_UPLOAD_MAX_BYTES = env_int(
    "ESIGN_LEASE_UPLOAD_MAX_BYTES",
    15 * 1024 * 1024,
    min_value=1024 * 1024,
    max_value=100 * 1024 * 1024,
)
ESIGN_SIGNATURE_MIN_BYTES = env_int(
    "ESIGN_SIGNATURE_MIN_BYTES", 250, min_value=50, max_value=10000
)
ESIGN_SIGNATURE_MAX_BYTES = env_int(
    "ESIGN_SIGNATURE_MAX_BYTES", 512 * 1024, min_value=1024, max_value=5 * 1024 * 1024
)
ESIGN_SIGNATURE_MIN_WIDTH = env_int(
    "ESIGN_SIGNATURE_MIN_WIDTH", 20, min_value=1, max_value=8000
)
ESIGN_SIGNATURE_MIN_HEIGHT = env_int(
    "ESIGN_SIGNATURE_MIN_HEIGHT", 10, min_value=1, max_value=8000
)
ESIGN_SIGNATURE_MAX_WIDTH = env_int(
    "ESIGN_SIGNATURE_MAX_WIDTH", 4000, min_value=100, max_value=8000
)
ESIGN_SIGNATURE_MAX_HEIGHT = env_int(
    "ESIGN_SIGNATURE_MAX_HEIGHT", 2000, min_value=50, max_value=8000
)

# Logging - workflow steps use INFO on app loggers (payments, messaging, accounts).
# Tests use assertLogs on the same logger names (e.g. payments.views).
_LOG_HANDLER = "test_console" if TESTING else "console"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "test_console": {
            "class": "logging.StreamHandler",
            "level": "CRITICAL",
            "formatter": "verbose",
        },
    },
    "loggers": {
        # Hierarchical: payments.*, messaging.*, accounts.* attach here
        "payments": {
            "handlers": [_LOG_HANDLER],
            "level": "INFO",
            "propagate": False,
        },
        "messaging": {
            "handlers": [_LOG_HANDLER],
            "level": "INFO",
            "propagate": False,
        },
        "accounts": {
            "handlers": [_LOG_HANDLER],
            "level": "INFO",
            "propagate": False,
        },
        "esign": {
            "handlers": [_LOG_HANDLER],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": [_LOG_HANDLER],
        "level": "INFO",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
