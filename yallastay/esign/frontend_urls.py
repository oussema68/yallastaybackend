"""Resolve public web origin from Django settings (FRONTEND_URL)."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def frontend_base_url() -> str:
    """Trailing slashes stripped; requires FRONTEND_URL in settings."""
    url = str(getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
    if not url:
        raise ImproperlyConfigured(
            "FRONTEND_URL is not configured. Set it in .env (see .env.example)."
        )
    return url
