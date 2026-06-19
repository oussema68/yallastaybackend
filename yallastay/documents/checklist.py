"""
Expected document categories per role for UAE-aligned onboarding (supporting documents).

**Identity verification (all roles):** Official *verified* status for natural persons is driven by
the **UAE ID integration** (``accounts.UAEIDVerification`` + future live API) - not by manual
approval of passport/visa scans alone.

**Tenants:** Upload **passport** and **residence visa** as supporting KYC; *gate* for platform
features that require verified identity remains **UAE ID verification approved**.

**Realtors:** Passport, visa, trade licence, RERA Broker Card (BRN), and brokerage licence
for admin/platform verification. **ORN** and **agency / supplementary licence** apply when
``RealtorProfile.brokerage_type == "agency"`` (optional where not applicable).

**Owners (landlords):** UAE ID (supporting scan), passport, and **residence visa** if not
Emirati (``LandlordProfile.is_emirati is False``). **Title deeds** are attached per **listing**
(``Listing.title_deed_document``), not only on the profile - one listing per deed.

Uses ``Document.document_type`` keys from ``documents.models.Document.DOCUMENT_TYPES``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

# Order matters for human-readable checklists in emails.
CHECKLIST_BY_ROLE: dict[str, list[str]] = {
    # Supporting docs only; UAE ID verification is via UAEIDVerification / API.
    "tenant": [
        "passport",
        "residence_visa",
    ],
    "student": [
        "passport",
        "residence_visa",
        "university",
    ],
    "realtor": [
        "passport",
        "residence_visa",
        "trade_license",
        "rera_broker_card",
        "realtor_license",
    ],
    # ORN + agency licence: required when brokerage_type is agency (see optional below).
    "landlord": [
        "uae_id",
        "passport",
    ],
}

# Types suggested when the realtor works under an agency (admin may waive).
REALTOR_AGENCY_OPTIONAL: list[str] = [
    "orn",
    "agency_supplementary_licence",
    "noc_agency",
]

ROLE_LABEL = {
    "realtor": "Realtor (broker)",
    "landlord": "Property owner (landlord)",
    "tenant": "Tenant (renter)",
    "student": "Student (renter, university verified)",
}


def profile_role(user: AbstractUser) -> str | None:
    try:
        return (user.profile.role or "").strip() or None
    except Exception:
        return None


def checklist_for_role(role: str | None) -> list[str]:
    if not role:
        return ["other"]
    return list(CHECKLIST_BY_ROLE.get(role, ["other"]))


def _landlord_extra_visa_types(user: AbstractUser) -> list[str]:
    """Non-Emirati owners must upload a residence visa."""
    try:
        lp = user.landlord_profile
    except Exception:
        return []
    if lp.is_emirati is False:
        return ["residence_visa"]
    return []


def _realtor_agency_optional_types(user: AbstractUser) -> list[str]:
    try:
        rp = user.realtor_profile
    except Exception:
        return []
    if getattr(rp, "brokerage_type", None) == "agency":
        return list(REALTOR_AGENCY_OPTIONAL)
    return []


def full_checklist_for_user(user: AbstractUser) -> list[str]:
    """Required + conditional document types for this user."""
    role = profile_role(user)
    base = checklist_for_role(role)
    if role == "landlord":
        base = base + _landlord_extra_visa_types(user)
    if role == "realtor":
        base = base + _realtor_agency_optional_types(user)
    # Dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in base:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def present_and_missing(user: AbstractUser) -> tuple[list[str], list[str], list[str]]:
    """
    Returns (present_types, missing_types, full_checklist) using distinct uploaded types.
    """
    from .models import Document

    checklist = full_checklist_for_user(user)
    uploaded = set(
        Document.objects.filter(user=user).values_list("document_type", flat=True)
    )
    present = [t for t in checklist if t in uploaded]
    missing = [t for t in checklist if t not in uploaded]
    return present, missing, checklist


def document_type_label(document_type: str) -> str:
    from .models import Document

    return dict(Document.DOCUMENT_TYPES).get(document_type, document_type)
