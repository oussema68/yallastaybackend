"""
Who may read uploaded files (not modify). Owners always see their own; listing brokers
and parties see title deed + landlord identity docs for compliance / Trakheesi workflow.
"""

from typing import Optional

from django.db.models import Q


def _verification_staff_can_read_all(user) -> bool:
    from accounts.staff_permissions import user_can_access_staff_verification

    return user_can_access_staff_verification(user)


# Supporting scans uploaded under Documents for the landlord party
IDENTITY_DOCUMENT_TYPES = frozenset({"uae_id", "passport", "residence_visa"})


def identity_subject_user_id(listing) -> Optional[int]:
    """User id whose ownership / ID applies to this listing (landlord party)."""
    if listing.property_owner_id:
        return listing.property_owner_id
    try:
        lb = listing.listed_by
        if lb is not None and getattr(lb.profile, "role", None) == "landlord":
            return listing.listed_by_id
    except Exception:
        pass
    return None


def user_can_view_listing_compliance_files(user, listing) -> bool:
    """Lister, assigned broker, or property owner may view deed + owner ID files for this listing."""
    if not user.is_authenticated:
        return False
    uid = user.id
    if listing.listed_by_id == uid:
        return True
    if listing.property_owner_id == uid:
        return True
    if listing.assigned_realtor_id == uid:
        return True
    return False


def user_can_read_document(user, doc) -> bool:
    """
    Read-only access to a Document row (GET /api/documents/:id/).
    Owner always; otherwise listing-based rules for brokers and parties.
    """
    if not user.is_authenticated:
        return False
    if doc.user_id == user.id:
        return True

    if _verification_staff_can_read_all(user):
        return True

    from listings.models import Listing

    # Title deed PDF linked on the listing
    if doc.document_type == "title_deed":
        return (
            Listing.objects.filter(title_deed_document_id=doc.id)
            .filter(
                Q(listed_by_id=user.id)
                | Q(assigned_realtor_id=user.id)
                | Q(property_owner_id=user.id)
            )
            .exists()
        )

    if doc.document_type not in IDENTITY_DOCUMENT_TYPES:
        return False

    # Landlord party's supporting ID/passport uploads (Documents app)
    for listing in Listing.objects.filter(
        Q(listed_by_id=user.id) | Q(assigned_realtor_id=user.id)
    ).select_related("listed_by"):
        subj = identity_subject_user_id(listing)
        if subj and subj == doc.user_id:
            return True
    return False
