"""Resolve public web origin from Django settings (FRONTEND_URL)."""

from __future__ import annotations

from django.conf import settings


def frontend_base_url() -> str:
    """Trailing slashes stripped; default only when settings left blank."""
    return str(getattr(settings, "FRONTEND_URL", "") or "http://localhost:3000").rstrip(
        "/"
    )
