"""Accept a listing owner invite and link property_owner."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from notifications.services import notify_user

from .assignment import is_landlord_user, validate_property_owner_target
from .emails_assignment import send_property_owner_linked_email
from .models import Listing, ListingOwnerInvite
from .notifications import notify_property_owner_linked


class OwnerInviteError(Exception):
    def __init__(self, message: str, *, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


@transaction.atomic
def accept_listing_owner_invite(*, token: str, user) -> Listing:
    """
    Link ``user`` as ``property_owner`` on the invite's listing.
    Requires landlord role and matching invite email (case-insensitive).
    """
    if not is_landlord_user(user):
        raise OwnerInviteError(
            "Only landlord accounts can accept a property owner invite. "
            "Register or sign in as a landlord first.",
            status=403,
        )

    invite = (
        ListingOwnerInvite.objects.select_for_update()
        .select_related("listing", "listing__listed_by", "invited_by")
        .filter(token=token)
        .first()
    )
    if not invite:
        raise OwnerInviteError(
            "This invite link is invalid or has expired.", status=404
        )
    if invite.accepted_at:
        listing = invite.listing
        if invite.accepted_by_id == user.id:
            return listing
        raise OwnerInviteError(
            "This invite was already used by another account.", status=400
        )

    if user.email.lower() != invite.email.lower():
        raise OwnerInviteError(
            "Sign in with the email address that received the invite "
            f"({invite.email}).",
            status=403,
        )

    listing = invite.listing
    if listing.property_owner_id and listing.property_owner_id != user.id:
        raise OwnerInviteError(
            "This listing already has a different property owner linked.", status=400
        )

    validate_property_owner_target(user)

    Listing.objects.filter(pk=listing.pk).update(property_owner_id=user.id)
    ListingOwnerInvite.objects.filter(pk=invite.pk).update(
        accepted_at=timezone.now(),
        accepted_by_id=user.id,
    )
    listing.refresh_from_db()

    realtor = invite.invited_by
    from messaging.partnership import ensure_partnership_conversation

    conv = ensure_partnership_conversation(
        listing,
        opened_by=user,
        intro_text=(
            "Thanks for accepting the owner invite. "
            "Share your title deed and any supporting documents here."
        ),
    )
    messages_link = f"/messages?conversation={conv.id}" if conv else None
    notify_property_owner_linked(user, listing, realtor=realtor, link=messages_link)
    send_property_owner_linked_email(user, listing, realtor=realtor)
    notify_user(
        realtor,
        "listing",
        "Property owner accepted your invite",
        f"{user.first_name or user.email} is now linked as owner of “{listing.title}”.",
        link=messages_link or f"/property/{listing.pk}/",
    )
    if conv:
        notify_user(
            user,
            "listing",
            "Broker chat opened",
            f"Messages with your broker for “{listing.title}” are ready.",
            link=messages_link,
        )
    return listing
