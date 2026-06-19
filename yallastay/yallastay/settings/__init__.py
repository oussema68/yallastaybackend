"""
Django settings module.
Imports settings based on DJANGO_ENV (dev/prod).
"""

import os

ENVIRONMENT = os.environ.get("DJANGO_ENV", "").strip().lower()
if ENVIRONMENT not in ("prod", "production"):
    if os.environ.get("RAILWAY_ENVIRONMENT_NAME") or os.environ.get(
        "RAILWAY_ENVIRONMENT_ID"
    ):
        ENVIRONMENT = "prod"
    elif os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PRIVATE_URL"):
        ENVIRONMENT = "prod"

if ENVIRONMENT in ("prod", "production"):
    from .prod import *  # noqa: F403
else:
    from .dev import *  # noqa: F403
