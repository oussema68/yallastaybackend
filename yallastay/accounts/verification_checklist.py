"""
Document checklists for staff review of broker (realtor) and owner (landlord) accounts.

Product rules align with ``docs/product/uae-verification-pipeline.md`` (not legal advice).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model

User = get_user_model()


@dataclass(frozen=True)
class ChecklistItem:
    key: str
    label: str
    required: bool


def _latest_doc_ids_by_type(user_id: int) -> dict[str, dict[str, Any]]:
    """Most recent upload per ``document_type`` for this user."""
    from documents.models import Document

    out: dict[str, dict[str, Any]] = {}
    for d in Document.objects.filter(user_id=user_id).order_by("-created_at"):
        if d.document_type not in out:
            out[d.document_type] = {"id": d.id, "created_at": d.created_at.isoformat()}
    return out


def realtor_checklist_items(brokerage_type: str) -> list[ChecklistItem]:
    base = [
        ChecklistItem("trade_license", "Trade licence (DET / Free Zone)", True),
        ChecklistItem("rera_broker_card", "RERA broker card (BRN)", True),
        ChecklistItem("passport", "Passport", True),
        ChecklistItem("residence_visa", "Residence visa", True),
        ChecklistItem("realtor_license", "Brokerage / licence upload (PDF)", False),
    ]
    if brokerage_type == "agency":
        base.extend(
            [
                ChecklistItem("orn", "ORN (Office Registration Number)", True),
                ChecklistItem(
                    "agency_supplementary_licence",
                    "Agency / supplementary licence",
                    False,
                ),
                ChecklistItem("noc_agency", "NOC (sponsoring agency)", False),
            ]
        )
    return base


def build_realtor_checklist(user: User) -> list[dict[str, Any]]:
    from accounts.models import RealtorProfile

    try:
        rp = user.realtor_profile
    except RealtorProfile.DoesNotExist:
        return []
    by_type = _latest_doc_ids_by_type(user.id)
    rows = []
    for item in realtor_checklist_items(rp.brokerage_type):
        meta = by_type.get(item.key)
        rows.append(
            {
                "key": item.key,
                "label": item.label,
                "required": item.required,
                "present": meta is not None,
                "document_id": meta["id"] if meta else None,
                "uploaded_at": meta.get("created_at") if meta else None,
            }
        )
    return rows


def landlord_checklist_items(is_emirati: bool | None) -> list[ChecklistItem]:
    items = [
        ChecklistItem("passport", "Passport", True),
        ChecklistItem("uae_id", "Emirates ID (supporting scan)", True),
    ]
    if is_emirati is False:
        items.append(
            ChecklistItem("residence_visa", "Residence visa (non-Emirati)", True)
        )
    elif is_emirati is None:
        items.append(
            ChecklistItem(
                "residence_visa",
                "Residence visa (required if not Emirati — confirm profile)",
                False,
            )
        )
    return items


def build_landlord_checklist(user: User) -> list[dict[str, Any]]:
    from accounts.models import LandlordProfile

    try:
        lp = user.landlord_profile
    except LandlordProfile.DoesNotExist:
        return []
    by_type = _latest_doc_ids_by_type(user.id)
    rows = []
    for item in landlord_checklist_items(lp.is_emirati):
        meta = by_type.get(item.key)
        rows.append(
            {
                "key": item.key,
                "label": item.label,
                "required": item.required,
                "present": meta is not None,
                "document_id": meta["id"] if meta else None,
                "uploaded_at": meta.get("created_at") if meta else None,
            }
        )
    return rows


def realtor_checklist_complete(user: User) -> bool:
    rows = build_realtor_checklist(user)
    return bool(rows) and all(not r["required"] or r["present"] for r in rows)


def landlord_checklist_complete(user: User) -> bool:
    rows = build_landlord_checklist(user)
    return bool(rows) and all(not r["required"] or r["present"] for r in rows)
