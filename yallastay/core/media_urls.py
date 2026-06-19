"""Absolute URLs for FileField/ImageField: local /media/ or S3 signed URLs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.core.files import File
    from django.http import HttpRequest


def absolute_media_url(request: HttpRequest | None, file: File | None) -> str | None:
    """
    Return a browser-usable URL for a stored file.

    With default filesystem storage, ``file.url`` is often relative (``/media/...``);
    with S3 (``django-storages``), ``file.url`` is usually already an https URL with
    query-string auth: pass through without double-wrapping ``request.build_absolute_uri``.
    """
    if not file:
        return None
    try:
        url = file.url
    except Exception:
        return None
    if not url:
        return None
    if url.startswith(("http://", "https://")):
        return url
    if request is not None:
        return request.build_absolute_uri(url)
    return url
