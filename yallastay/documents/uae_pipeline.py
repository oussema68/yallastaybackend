"""
UAE-aligned verification helpers (product rules; not legal advice).

- **UAE ID:** The authoritative *identity* check for tenants and owners is Emirates ID
  verification (``UAEIDVerification`` + planned live API). Passport / visa uploads are
  supporting documents for compliance and admin review.

- **Realtors:** Document set aligns with Dubai DLD / RERA expectations (trade licence, BRN,
  etc.). Platform approval remains ``RealtorProfile.is_approved``.

- **Owners:** One **listing** row per **title deed** upload; deed reference text must match
  the document. Owners pick from **verified** realtors only; private brokers sort before
  agency brokers for less paperwork.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Case, IntegerField, When

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


def uae_id_verification_approved(user: AbstractUser) -> bool:
    """True if Emirates ID record exists and status is approved."""
    try:
        v = user.uae_id_verification
    except Exception:
        return False
    return v.status == "approved"


def verified_realtors_queryset():
    """Approved realtors; private brokers first, then agency (name)."""
    from accounts.models import RealtorProfile

    return (
        RealtorProfile.objects.filter(is_approved=True)
        .select_related("user")
        .annotate(
            _sort_private_first=Case(
                When(brokerage_type="private", then=0),
                default=1,
                output_field=IntegerField(),
            )
        )
        .order_by("_sort_private_first", "agency_name", "user_id")
    )
