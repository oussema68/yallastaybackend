"""Validate and normalize realtor-defined signature field boxes (PDF coordinates)."""

from __future__ import annotations

import io
from typing import Any

from pypdf import PdfReader

# New dashboard flow: three placement areas per party (e.g. Ejari-style multi-page).
# Legacy sessions may still have a single rect per role (dict).
_ALLOWED_COUNTS = frozenset({0, 1, 3})


def _rect_from_dict(d: dict[str, Any]) -> dict[str, float | int] | None:
    if not isinstance(d, dict):
        return None
    try:
        page_index = int(d["page_index"])
        x = float(d["x"])
        y = float(d["y"])
        width = float(d["width"])
        height = float(d["height"])
    except (KeyError, TypeError, ValueError):
        return None
    if page_index < 0 or width <= 0 or height <= 0:
        return None
    return {
        "page_index": page_index,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
    }


def _coerce_role_rects(val: Any) -> list[dict[str, float | int]] | None:
    """Single dict (legacy), list of dicts, or empty."""
    if val is None:
        return []
    if isinstance(val, dict):
        r = _rect_from_dict(val)
        return [r] if r else None
    if isinstance(val, list):
        out: list[dict[str, float | int]] = []
        for it in val:
            r = _rect_from_dict(it) if isinstance(it, dict) else None
            if not r:
                return None
            out.append(r)
        return out
    return None


def normalize_signature_field_boxes(raw: Any) -> dict[str, Any] | None:
    """
    Expects {"renter": [...], "lister": [...]} with 0, 1 (legacy), or 3 rects each,
    or legacy single dict per role. PDF user-space coords (points, origin bottom-left).

    Partial save: renter may have 3 rects and lister [] until the second step.
    """
    if raw is None or raw == {}:
        return None
    if not isinstance(raw, dict):
        return None
    renter_list = _coerce_role_rects(raw.get("renter"))
    lister_list = _coerce_role_rects(raw.get("lister"))
    if renter_list is None or lister_list is None:
        return None
    if (
        len(renter_list) not in _ALLOWED_COUNTS
        or len(lister_list) not in _ALLOWED_COUNTS
    ):
        return None
    if len(renter_list) == 0 and len(lister_list) == 0:
        return None
    return {"renter": renter_list, "lister": lister_list}


def validate_boxes_fit_pdf(pdf_bytes: bytes, boxes: dict[str, Any]) -> str | None:
    """Return error message or None if OK."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        n = len(reader.pages)
    except Exception:
        return "Could not read the contract PDF."

    def check_rect(role: str, r: dict[str, Any]) -> str | None:
        pi = int(r["page_index"])
        if pi >= n:
            return f"{role} page_index {pi} is out of range (PDF has {n} page(s))."
        page = reader.pages[pi]
        mb = page.mediabox
        pw = float(mb.width)
        ph = float(mb.height)
        x, y, w, h = r["x"], r["y"], r["width"], r["height"]
        if x < 0 or y < 0 or x + w > pw + 1 or y + h > ph + 1:
            return f"{role} signature box is outside the page bounds."
        return None

    for role in ("renter", "lister"):
        seq = boxes[role]
        if isinstance(seq, dict):
            seq = [seq]
        for i, r in enumerate(seq):
            err = check_rect(f"{role}[{i}]", r)
            if err:
                return err
    return None
