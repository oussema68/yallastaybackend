"""Resize and compress user-uploaded listing photos before storage."""

from __future__ import annotations

import io
import os
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

# Defaults; override via settings / env in base.py
DEFAULT_LISTING_IMAGE_MAX_WIDTH = 1600
DEFAULT_LISTING_IMAGE_JPEG_QUALITY = 82
DEFAULT_LISTING_IMAGE_MAX_BYTES = 900_000
DEFAULT_LISTING_THUMB_MAX_WIDTH = 480
DEFAULT_LISTING_THUMB_JPEG_QUALITY = 78


def _setting(name: str, default):
    return getattr(settings, name, default)


def _unique_name(original_name: str, suffix: str) -> str:
    base = os.path.basename(original_name or "upload.jpg")
    stem, _ext = os.path.splitext(base)
    safe_stem = (
        "".join(c if c.isalnum() or c in "-_" else "-" for c in stem)[:80] or "photo"
    )
    return f"{safe_stem}-{uuid.uuid4().hex[:10]}{suffix}"


def _encode_jpeg(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def _fit_jpeg(
    img: Image.Image,
    *,
    max_width: int,
    quality: int,
    max_bytes: int,
) -> bytes:
    if img.width > max_width:
        ratio = max_width / img.width
        new_h = max(1, int(img.height * ratio))
        img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)

    data = _encode_jpeg(img, quality)
    q = quality
    while len(data) > max_bytes and q > 50:
        q -= 8
        data = _encode_jpeg(img, q)
    while len(data) > max_bytes and img.width > 640:
        new_w = max(640, int(img.width * 0.85))
        ratio = new_w / img.width
        img = img.resize(
            (new_w, max(1, int(img.height * ratio))), Image.Resampling.LANCZOS
        )
        data = _encode_jpeg(img, q)
    return data


def prepare_listing_image_upload(uploaded) -> tuple[ContentFile, ContentFile]:
    """
    Return (main_image, thumbnail) ContentFiles ready for ImageField.save().

    Accepts Django UploadedFile or any file-like object with .read().
    """
    max_w = _setting("LISTING_IMAGE_MAX_WIDTH", DEFAULT_LISTING_IMAGE_MAX_WIDTH)
    quality = _setting("LISTING_IMAGE_JPEG_QUALITY", DEFAULT_LISTING_IMAGE_JPEG_QUALITY)
    max_bytes = _setting("LISTING_IMAGE_MAX_BYTES", DEFAULT_LISTING_IMAGE_MAX_BYTES)
    thumb_w = _setting("LISTING_THUMB_MAX_WIDTH", DEFAULT_LISTING_THUMB_MAX_WIDTH)
    thumb_q = _setting("LISTING_THUMB_JPEG_QUALITY", DEFAULT_LISTING_THUMB_JPEG_QUALITY)

    original_name = getattr(uploaded, "name", "upload.jpg")
    if hasattr(uploaded, "seek"):
        uploaded.seek(0)
    raw = uploaded.read()
    if hasattr(uploaded, "seek"):
        uploaded.seek(0)

    with Image.open(io.BytesIO(raw)) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        main_bytes = _fit_jpeg(
            im.copy(),
            max_width=max_w,
            quality=quality,
            max_bytes=max_bytes,
        )
        thumb_img = im.copy()
        if thumb_img.width > thumb_w:
            ratio = thumb_w / thumb_img.width
            thumb_img = thumb_img.resize(
                (thumb_w, max(1, int(thumb_img.height * ratio))),
                Image.Resampling.LANCZOS,
            )
        thumb_bytes = _encode_jpeg(thumb_img, thumb_q)

    main_name = _unique_name(original_name, ".jpg")
    thumb_name = _unique_name(original_name, "-thumb.jpg")
    main = ContentFile(main_bytes, name=main_name)
    thumb = ContentFile(thumb_bytes, name=thumb_name)
    main.content_type = "image/jpeg"
    thumb.content_type = "image/jpeg"
    return main, thumb
