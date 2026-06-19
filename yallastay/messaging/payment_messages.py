"""Post Yallastay Team messages when rental-related payments complete."""

import logging

from django.utils import timezone

from messaging.models import Conversation, Message
from messaging.team_user import get_or_create_yallastay_team_user

logger = logging.getLogger(__name__)


def get_or_create_listing_conversation(listing, renter, lister):
    """Same pairing as starting a chat from a listing (one thread per pair + listing)."""
    conv = (
        Conversation.objects.filter(listing=listing)
        .filter(participants=renter)
        .filter(participants=lister)
        .distinct()
        .first()
    )
    if not conv:
        conv = Conversation.objects.create(listing=listing)
        conv.participants.add(renter, lister)
    return conv


def build_payment_received_message(payment) -> str:
    reservation = payment.reservation
    listing = reservation.listing
    renter = payment.user
    renter_name = (renter.first_name or "").strip() or "The renter"
    ptype = payment.get_payment_type_display()
    amount_s = f"{payment.amount} {payment.currency}".strip()
    lines = [
        "Hello - this is an automated message from the Yallastay team.",
        "",
        f"{renter_name} has completed a {ptype.lower()} payment ({amount_s}) for this rental.",
        f"Listing: {listing.title}",
        f"Lease window: {reservation.start_date} → {reservation.end_date}.",
        "",
        "Please coordinate with the renter to finalize the tenancy (contract / Ejari and handover) using the contact details you already have or those shared in this thread.",
        "If anything is missing for your internal checklist, reply here or reach out through Yallastay support.",
        "",
        " -  Yallastay",
    ]
    return "\n".join(lines)


def notify_realtor_rental_payment_received(payment) -> bool:
    """
    If this is a completed rent/deposit tied to a reservation, post one team message
    to the listing conversation (renter + lister). Returns True if a message was sent.
    """
    if payment.team_message_sent_at:
        logger.info(
            "payment.team_message.skip: payment_id=%s reason=already_sent",
            payment.id,
        )
        return False
    if payment.status != "completed":
        logger.info(
            "payment.team_message.skip: payment_id=%s reason=not_completed status=%s",
            payment.id,
            payment.status,
        )
        return False
    if payment.payment_type not in ("rent", "deposit"):
        logger.info(
            "payment.team_message.skip: payment_id=%s reason=wrong_type type=%s",
            payment.id,
            payment.payment_type,
        )
        return False
    if not payment.reservation_id:
        logger.info(
            "payment.team_message.skip: payment_id=%s reason=no_reservation",
            payment.id,
        )
        return False

    reservation = payment.reservation
    listing = reservation.listing
    renter = payment.user
    lister = listing.listed_by

    conv = get_or_create_listing_conversation(listing, renter, lister)
    team = get_or_create_yallastay_team_user()
    body = build_payment_received_message(payment)

    Message.objects.create(conversation=conv, sender=team, content=body)
    now = timezone.now()
    conv.updated_at = now
    conv.save(update_fields=["updated_at"])

    payment.team_message_sent_at = now
    payment.save(update_fields=["team_message_sent_at"])
    logger.info(
        "payment.team_message.sent: payment_id=%s conversation_id=%s listing_id=%s",
        payment.id,
        conv.id,
        listing.id,
    )
    return True
