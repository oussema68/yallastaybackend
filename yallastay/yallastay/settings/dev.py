"""
Development settings.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import TESTING
from .env_util import env_csv, env_str

DEBUG = True

if TESTING:
    ALLOWED_HOSTS = env_csv("ALLOWED_HOSTS") or ["testserver"]
    CORS_ALLOWED_ORIGINS = env_csv("CORS_ALLOWED_ORIGINS")
    FRONTEND_URL = env_str("FRONTEND_URL") or "http://testserver"
    BACKEND_URL = env_str("BACKEND_URL") or "http://testserver"
else:
    ALLOWED_HOSTS = env_csv("ALLOWED_HOSTS")
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS must be set in .env for local dev (see .env.example)."
        )

    CORS_ALLOWED_ORIGINS = env_csv("CORS_ALLOWED_ORIGINS")
    if not CORS_ALLOWED_ORIGINS:
        raise ImproperlyConfigured(
            "CORS_ALLOWED_ORIGINS must be set in .env for local dev (see .env.example)."
        )

    FRONTEND_URL = env_str("FRONTEND_URL")
    BACKEND_URL = env_str("BACKEND_URL")
    if not FRONTEND_URL or not BACKEND_URL:
        raise ImproperlyConfigured(
            "FRONTEND_URL and BACKEND_URL must be set in .env for local dev (see .env.example)."
        )

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# Allow `manage.py dev_reset_esign_session` - off under the test runner (`TESTING`).
ESIGN_DEV_RESET_ENABLED = not TESTING
