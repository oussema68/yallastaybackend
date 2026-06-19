"""Tests for signature_field_boxes normalization."""

from django.test import SimpleTestCase

from esign.signature_boxes import normalize_signature_field_boxes

_RECT = {"page_index": 0, "x": 10, "y": 10, "width": 50, "height": 20}


class SignatureBoxesTests(SimpleTestCase):
    def test_normalize_three_renter_empty_lister(self):
        raw = {"renter": [_RECT, _RECT, _RECT], "lister": []}
        norm = normalize_signature_field_boxes(raw)
        self.assertIsNotNone(norm)
        self.assertEqual(len(norm["renter"]), 3)
        self.assertEqual(len(norm["lister"]), 0)

    def test_normalize_full_six(self):
        raw = {"renter": [_RECT, _RECT, _RECT], "lister": [_RECT, _RECT, _RECT]}
        norm = normalize_signature_field_boxes(raw)
        self.assertIsNotNone(norm)
        self.assertEqual(len(norm["renter"]), 3)
        self.assertEqual(len(norm["lister"]), 3)

    def test_normalize_legacy_single_dict(self):
        raw = {
            "renter": {"page_index": 0, "x": 1, "y": 2, "width": 10, "height": 10},
            "lister": {"page_index": 0, "x": 1, "y": 20, "width": 10, "height": 10},
        }
        norm = normalize_signature_field_boxes(raw)
        self.assertIsNotNone(norm)
        self.assertEqual(len(norm["renter"]), 1)
        self.assertEqual(len(norm["lister"]), 1)

    def test_reject_two_rects(self):
        raw = {"renter": [_RECT, _RECT], "lister": []}
        self.assertIsNone(normalize_signature_field_boxes(raw))
