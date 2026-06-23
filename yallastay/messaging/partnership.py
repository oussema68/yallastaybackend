"""Owner ↔ broker conversations when a listing assignment is active."""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model

from listings.models import Listing

from .models import Conversation, Message

User = get_user_model()
logger = logging.getLogger(__name__)

DEFAULT_INTRO = (
    "You're connected here to coordinate on this listing - share documents, "
    "Trakheesi updates, and title deed details."
)


def partnership_parties(listing: Listing) -> tuple[User, User] | None:
    """
    Return (owner_user, broker_user) when an assignment exists.

    - Landlord self-listed + assigned_realtor
    - Realtor-listed + property_owner
    """
    listed_by = listing.listed_by
    if not listing.listed_by_id:
        return None

    try:
        lister_role = listed_by.profile.role
    except Exception:
        lister_role = None

    if lister_role == "landlord" and listing.assigned_realtor_id:
        return listed_by, listing.assigned_realtor

    if lister_role == "realtor" and listing.property_owner_id:
        return listing.property_owner, listed_by

    return None


def ensure_partnership_conversation(
    listing: Listing,
    *,
    opened_by: User | None = None,
    intro_text: str | None = None,
) -> Conversation | None:
    """
    Create or refresh the owner-broker thread for this listing.
    Called when assigned_realtor or property_owner is set/changed.
    """
    parties = partnership_parties(listing)
    if not parties:
        return None

    owner, broker = parties
    conv, created = Conversation.objects.get_or_create(
        listing=listing,
        kind=Conversation.KIND_PARTNERSHIP,
    )
    conv.participants.set([owner, broker])

    if created:
        sender = (
            opened_by if opened_by and opened_by.pk in (owner.pk, broker.pk) else owner
        )
        Message.objects.create(
            conversation=conv,
            sender=sender,
            content=intro_text or DEFAULT_INTRO,
        )
        logger.info(
            "messaging.partnership.create: listing_id=%s conversation_id=%s owner_id=%s broker_id=%s",
            listing.pk,
            conv.pk,
            owner.pk,
            broker.pk,
        )
    else:
        logger.info(
            "messaging.partnership.refresh: listing_id=%s conversation_id=%s",
            listing.pk,
            conv.pk,
        )

    return conv
