"""
Development settings.
"""

import os

from .base import *  # noqa: F403
from .base import TESTING
from .env_util import env_csv, env_str

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
_env_hosts = (os.environ.get("ALLOWED_HOSTS") or "").strip()
if _env_hosts:
    ALLOWED_HOSTS = list(ALLOWED_HOSTS) + [
        h.strip() for h in _env_hosts.split(",") if h.strip()
    ]

# Override with comma-separated CORS_ALLOWED_ORIGINS in .env when needed.
_default_dev_cors = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
_cors_from_env = env_csv("CORS_ALLOWED_ORIGINS")
CORS_ALLOWED_ORIGINS = _cors_from_env if _cors_from_env else _default_dev_cors
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

FRONTEND_URL = env_str("FRONTEND_URL") or "http://localhost:3000"
BACKEND_URL = env_str("BACKEND_URL") or "http://localhost:8000"

# Allow `manage.py dev_reset_esign_session` - off under the test runner (`TESTING`).
ESIGN_DEV_RESET_ENABLED = not TESTING
