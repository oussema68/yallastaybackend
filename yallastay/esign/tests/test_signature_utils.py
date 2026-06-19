"""Unit tests for PNG signature decode/validate helpers (no DB)."""

from __future__ import annotations

import base64
import io
import random
import unittest

from PIL import Image, ImageDraw

from esign.signature_utils import (
    MAX_SIGNATURE_BYTES,
    MIN_SIGNATURE_BYTES,
    decode_signature_png_payload,
    validate_signature_png,
)


def _stroke_png_bytes() -> bytes:
    buf = io.BytesIO()
    im = Image.new("RGB", (200, 80), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.line([(10, 40), (190, 40)], fill=(0, 0, 0), width=2)
    im.save(buf, format="PNG")
    return buf.getvalue()


def _tiny_png_under_min() -> bytes:
    """PNG smaller than MIN_SIGNATURE_BYTES (invalid for signing)."""
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _png_bad_dimensions() -> bytes:
    """Valid PNG but width under 20px; file large enough to pass size checks."""
    buf = io.BytesIO()
    im = Image.new("RGB", (18, 320))
    px = im.load()
    for y in range(320):
        for x in range(18):
            px[x, y] = (random.randint(0, 255), y % 256, x % 256)
    im.save(buf, format="PNG")
    return buf.getvalue()


class DecodeSignaturePayloadTests(unittest.TestCase):
    def test_none_and_empty(self):
        self.assertIsNone(decode_signature_png_payload(None))
        self.assertIsNone(decode_signature_png_payload(""))

    def test_rejects_non_string(self):
        self.assertIsNone(decode_signature_png_payload(123))  # type: ignore[arg-type]

    def test_raw_base64(self):
        raw = _stroke_png_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        out = decode_signature_png_payload(b64)
        self.assertEqual(out, raw)

    def test_data_url(self):
        raw = _stroke_png_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        url = f"data:image/png;base64,{b64}"
        out = decode_signature_png_payload(url)
        self.assertEqual(out, raw)

    def test_malformed_data_url(self):
        self.assertIsNone(decode_signature_png_payload("data:image/png;base64"))

    def test_invalid_base64(self):
        self.assertIsNone(decode_signature_png_payload("@@@not-base64!!!"))


class ValidateSignaturePngTests(unittest.TestCase):
    def test_missing(self):
        self.assertEqual(validate_signature_png(None), "missing_signature")
        self.assertEqual(validate_signature_png(b""), "missing_signature")

    def test_too_small(self):
        tiny = _tiny_png_under_min()
        self.assertLess(len(tiny), MIN_SIGNATURE_BYTES)
        self.assertEqual(validate_signature_png(tiny), "signature_too_small")

    def test_too_large(self):
        big = b"\x89PNG\r\n\x1a\n" + b"x" * (MAX_SIGNATURE_BYTES + 1)
        self.assertEqual(validate_signature_png(big), "signature_too_large")

    def test_not_png_magic(self):
        self.assertEqual(
            validate_signature_png(b"hello world " * 50), "invalid_signature_format"
        )

    def test_invalid_dimensions(self):
        bad = _png_bad_dimensions()
        self.assertGreaterEqual(
            len(bad),
            MIN_SIGNATURE_BYTES,
            "fixture must exceed min size so validation reaches dimension rules",
        )
        self.assertEqual(validate_signature_png(bad), "invalid_signature_dimensions")

    def test_valid_stroke_png(self):
        raw = _stroke_png_bytes()
        self.assertGreaterEqual(len(raw), MIN_SIGNATURE_BYTES)
        self.assertIsNone(validate_signature_png(raw))
