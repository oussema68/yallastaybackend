"""Plain-text sanitization for user-supplied strings (HTML stripped; XSS defense in depth)."""

from __future__ import annotations

import html

import bleach


def sanitize_plain_text(value: str | None) -> str:
    """
    Remove HTML tags and normalize user input intended for plain-text storage.
    Uses bleach with no allowed tags so markup cannot be persisted.
    Decodes HTML entities so plain text like ``<3`` or ``&`` round-trip for display.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    cleaned = bleach.clean(value, tags=[], attributes={}, strip=True)
    return html.unescape(cleaned).strip()
