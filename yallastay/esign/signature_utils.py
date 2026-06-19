"""Decode and validate PNG signatures from the signing API."""

from __future__ import annotations

import base64
import binascii
import io
import logging
import re

from PIL import Image

logger = logging.getLogger(__name__)


def __getattr__(name: str):
    """Expose limits for tests; values come from Django settings when configured."""
    if name == "MIN_SIGNATURE_BYTES":
        try:
            from django.conf import settings

            if settings.configured:
                return int(getattr(settings, "ESIGN_SIGNATURE_MIN_BYTES", 250))
        except Exception:
            pass
        return 250
    if name == "MAX_SIGNATURE_BYTES":
        try:
            from django.conf import settings

            if settings.configured:
                return int(getattr(settings, "ESIGN_SIGNATURE_MAX_BYTES", 512 * 1024))
        except Exception:
            pass
        return 512 * 1024
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _signature_limits():
    from django.conf import settings

    return (
        int(getattr(settings, "ESIGN_SIGNATURE_MIN_BYTES", 250)),
        int(getattr(settings, "ESIGN_SIGNATURE_MAX_BYTES", 512 * 1024)),
        int(getattr(settings, "ESIGN_SIGNATURE_MIN_WIDTH", 20)),
        int(getattr(settings, "ESIGN_SIGNATURE_MIN_HEIGHT", 10)),
        int(getattr(settings, "ESIGN_SIGNATURE_MAX_WIDTH", 4000)),
        int(getattr(settings, "ESIGN_SIGNATURE_MAX_HEIGHT", 2000)),
    )


def decode_signature_png_payload(raw: str | None) -> bytes | None:
    """Accept raw base64 or data URL; return bytes or None."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if s.startswith("data:image"):
        m = re.match(r"data:image/[^;]+;base64,(.+)", s, re.DOTALL)
        if not m:
            return None
        s = m.group(1).strip()
    try:
        return base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        return None


def validate_signature_png(data: bytes | None) -> str | None:
    """
    Return None if valid PNG signature image, else an error code for API responses.
    """
    min_b, max_b, min_w, min_h, max_w, max_h = _signature_limits()
    if not data:
        return "missing_signature"
    if len(data) < min_b:
        return "signature_too_small"
    if len(data) > max_b:
        return "signature_too_large"
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "invalid_signature_format"
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        logger.exception("esign.signature_png.verify_failed")
        return "invalid_signature_format"
    try:
        img = Image.open(io.BytesIO(data))
        w, h = img.size
        if w < min_w or h < min_h or w > max_w or h > max_h:
            return "invalid_signature_dimensions"
    except Exception:
        return "invalid_signature_format"
    return None
