"""
Production settings.
"""

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .env_util import env_bool, env_int, env_str

DEBUG = False

ESIGN_DEV_RESET_ENABLED = False

# FRONTEND_URL required for email links
FRONTEND_URL = env_str("FRONTEND_URL")
if not FRONTEND_URL:
    raise ImproperlyConfigured(
        "FRONTEND_URL must be set in production. Set it in your deployment env."
    )
if not FRONTEND_URL.startswith(("http://", "https://")):
    FRONTEND_URL = "https://" + FRONTEND_URL
elif FRONTEND_URL.startswith("http://"):
    FRONTEND_URL = "https://" + FRONTEND_URL[7:]

BACKEND_URL = env_str("BACKEND_URL")
if BACKEND_URL and not BACKEND_URL.startswith(("http://", "https://")):
    BACKEND_URL = "https://" + BACKEND_URL
elif BACKEND_URL and BACKEND_URL.startswith("http://"):
    BACKEND_URL = "https://" + BACKEND_URL[7:]

# PostgreSQL
DATABASE_URL = env_str("DATABASE_PRIVATE_URL") or env_str("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_PRIVATE_URL or DATABASE_URL must be set on your Django service."
    )
DATABASE_CONN_MAX_AGE = env_int(
    "DATABASE_CONN_MAX_AGE", 600, min_value=0, max_value=3600
)

DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=DATABASE_CONN_MAX_AGE,
        conn_health_checks=True,
    )
}

# Hosts & CORS
_raw_hosts = env_str("ALLOWED_HOSTS")
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(",") if h.strip()]
_railway_public = env_str("RAILWAY_PUBLIC_DOMAIN")
if _railway_public and _railway_public not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_public)
if not ALLOWED_HOSTS:
    raise ValueError(
        "ALLOWED_HOSTS must be set in production (comma-separated), "
        "or deploy on Railway with RAILWAY_PUBLIC_DOMAIN."
    )

if not BACKEND_URL and ALLOWED_HOSTS:
    BACKEND_URL = f"https://{ALLOWED_HOSTS[0]}"

_raw_origins = env_str("CORS_ALLOWED_ORIGINS")
CORS_ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-requested-with",
]

# Security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
# HSTS: set SECURE_HSTS_SECONDS=0 temporarily only if debugging HTTPS on first deploy
SECURE_HSTS_SECONDS = env_int(
    "SECURE_HSTS_SECONDS", 31536000, min_value=0, max_value=31536000
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)

# Email: prefer the Resend HTTPS API (set RESEND_API_KEY). If you fall back to SMTP,
# Railway containers have no IPv6 egress, so force IPv4 to avoid hanging connects.
# Override with EMAIL_SMTP_USE_IPV4=false if your host does route IPv6.
_smtp_ipv4 = (env_str("EMAIL_SMTP_USE_IPV4") or "").lower()
if _smtp_ipv4 in ("0", "false", "no", "off"):
    _use_ipv4_smtp = False
elif _smtp_ipv4 in ("1", "true", "yes", "on"):
    _use_ipv4_smtp = True
else:
    _use_ipv4_smtp = bool(
        env_str("RAILWAY_ENVIRONMENT_ID")
        or env_str("RAILWAY_ENVIRONMENT_NAME")
        or env_str("RAILWAY_SERVICE_ID")
    )
if _use_ipv4_smtp and EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
    EMAIL_BACKEND = "yallastay.mail_backends.IPv4EmailBackend"
