"""Helpers for multi-placement signing (one PNG per rectangle)."""

from __future__ import annotations

from typing import Any

from .models import LeaseSigningSession
from .signature_boxes import normalize_signature_field_boxes


def norm_boxes(session: LeaseSigningSession) -> dict[str, Any] | None:
    return normalize_signature_field_boxes(session.signature_field_boxes)


def role_rects_list(norm: dict[str, Any] | None, role: str) -> list[dict[str, Any]]:
    if not norm:
        return []
    v = norm.get(role)
    if isinstance(v, dict):
        return [v]
    if isinstance(v, list):
        return list(v)
    return []


def renter_placements_missing_for_lister_upload(session: LeaseSigningSession) -> bool:
    """
    When the lease PDF was uploaded by the realtor (not auto-generated), signature
    rectangles for the renter must exist before the renter can sign. Upload clears
    placements until PATCH signature_field_boxes saves them.
    """
    if not session.lister_contract_pdf:
        return False
    norm = norm_boxes(session)
    return len(role_rects_list(norm, "renter")) < 1


def is_multi_slot_role(norm: dict[str, Any] | None, role: str) -> bool:
    return len(role_rects_list(norm, role)) > 1


def count_renter_slots_saved(session: LeaseSigningSession) -> int:
    n = 0
    for i in range(1, 4):
        f = getattr(session, f"renter_signature_slot_{i}")
        if f and getattr(f, "name", None):
            n += 1
    return n


def count_lister_slots_saved(session: LeaseSigningSession) -> int:
    n = 0
    for i in range(1, 4):
        f = getattr(session, f"lister_signature_slot_{i}")
        if f and getattr(f, "name", None):
            n += 1
    return n
