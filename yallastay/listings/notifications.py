"""
In-app notifications for listing lifecycle.

Text is intentionally short (bell / notification center) - not copied from email templates.
"""

from __future__ import annotations

import logging

from notifications.services import notify_user

from .models import Listing

logger = logging.getLogger(__name__)


def notify_listing_published(user, listing: Listing, *, is_first: bool) -> None:
    try:
        if is_first:
            title = "Your first listing is live"
            body = f"“{listing.title}” is now visible to renters."
        else:
            title = "New listing added"
            body = f"“{listing.title}” was added to your listings."
        notify_user(
            user,
            "listing",
            title,
            body,
            link=f"/edit-property/{listing.id}",
        )
    except Exception:
        logger.exception(
            "notify_listing_published failed user_id=%s listing_id=%s",
            user.pk,
            listing.pk,
        )


def notify_broker_assigned(
    broker, listing: Listing, *, landlord, link: str | None = None
) -> None:
    """In-app alert when a landlord picks a verified broker on a self-listed unit."""
    try:
        landlord_name = (
            (getattr(landlord, "first_name", None) or "").strip()
            or getattr(landlord, "email", "")
            or "A landlord"
        )
        notify_user(
            broker,
            "listing",
            "You were assigned to a listing",
            f"{landlord_name} assigned you to “{listing.title}”. Open Messages to coordinate and share documents.",
            link=link or f"/property/{listing.pk}/",
        )
    except Exception:
        logger.exception(
            "notify_broker_assigned failed broker_id=%s listing_id=%s",
            broker.pk,
            listing.pk,
        )


def notify_property_owner_linked(
    owner, listing: Listing, *, realtor, link: str | None = None
) -> None:
    """In-app alert when a realtor links a landlord as property owner."""
    try:
        realtor_name = (
            (getattr(realtor, "first_name", None) or "").strip()
            or getattr(realtor, "email", "")
            or "Your realtor"
        )
        notify_user(
            owner,
            "listing",
            "You are linked as property owner",
            f"{realtor_name} linked you to “{listing.title}”. Open Messages to share your title deed and documents.",
            link=link or f"/property/{listing.pk}/",
        )
    except Exception:
        logger.exception(
            "notify_property_owner_linked failed owner_id=%s listing_id=%s",
            owner.pk,
            listing.pk,
        )


def notify_owner_invite_sent(listing: Listing, *, invite_email: str) -> None:
    """Optional confirmation to the inviting realtor."""
    try:
        notify_user(
            listing.listed_by,
            "listing",
            "Owner invite sent",
            f"Invitation emailed to {invite_email} for “{listing.title}”. They can accept after registering as a landlord.",
            link=f"/property/{listing.pk}/",
        )
    except Exception:
        logger.exception(
            "notify_owner_invite_sent failed listing_id=%s",
            listing.pk,
        )
