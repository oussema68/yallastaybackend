"""Transactional emails for owner ↔ realtor assignment."""

from __future__ import annotations

import logging

from django.conf import settings

from emails.services import (
    send_transactional_email,
    send_transactional_email_from_template,
)

from .models import Listing

logger = logging.getLogger(__name__)


def _frontend_url(path: str) -> str:
    base = (getattr(settings, "FRONTEND_URL", None) or "").rstrip("/")
    if not base:
        return path
    if path.startswith("/"):
        return f"{base}{path}"
    return f"{base}/{path}"


def send_broker_assigned_email(broker, listing: Listing, *, landlord) -> None:
    """Landlord assigned a verified broker to their self-listed unit."""
    if not broker or not getattr(broker, "email", None):
        return
    first = (getattr(broker, "first_name", None) or "").strip() or "there"
    landlord_name = (
        (getattr(landlord, "first_name", None) or "").strip()
        or getattr(landlord, "email", "")
        or "A landlord"
    )
    ctx = {
        "first_name": first,
        "landlord_name": landlord_name,
        "listing_title": listing.title,
        "listing_url": _frontend_url(f"/property/{listing.pk}/"),
        "workspace_url": _frontend_url("/my-listings"),
    }
    try:
        send_transactional_email_from_template(
            broker.email,
            "listing_broker_assigned",
            ctx,
            user=broker,
        )
    except ValueError as e:
        logger.warning("listing_broker_assigned template: %s", e)
        send_transactional_email(
            broker.email,
            subject=f"You were assigned to “{listing.title}” on Yallastay",
            body_text=(
                f"Hi {first},\n\n"
                f"{landlord_name} assigned you as their broker on “{listing.title}”.\n\n"
                f"Open the listing to add the Trakheesi permit and review owner documents:\n"
                f"{ctx['listing_url']}\n\n"
                f"Your broker workspace:\n{ctx['workspace_url']}\n\n"
                f" -  Yallastay"
            ),
            template_key="listing_broker_assigned",
        )
    except Exception:
        logger.exception(
            "listing_broker_assigned failed broker_id=%s listing_id=%s",
            broker.pk,
            listing.pk,
        )


def send_property_owner_linked_email(owner, listing: Listing, *, realtor) -> None:
    """Realtor linked a landlord as property owner on a broker-listed unit."""
    if not owner or not getattr(owner, "email", None):
        return
    first = (getattr(owner, "first_name", None) or "").strip() or "there"
    realtor_name = (
        (getattr(realtor, "first_name", None) or "").strip()
        or getattr(realtor, "email", "")
        or "Your realtor"
    )
    ctx = {
        "first_name": first,
        "realtor_name": realtor_name,
        "listing_title": listing.title,
        "listing_url": _frontend_url(f"/property/{listing.pk}/"),
        "profile_url": _frontend_url("/profile"),
    }
    try:
        send_transactional_email_from_template(
            owner.email,
            "listing_owner_linked",
            ctx,
            user=owner,
        )
    except ValueError as e:
        logger.warning("listing_owner_linked template: %s", e)
        send_transactional_email(
            owner.email,
            subject=f"You are linked as owner of “{listing.title}”",
            body_text=(
                f"Hi {first},\n\n"
                f"{realtor_name} linked you as the property owner for “{listing.title}” on Yallastay.\n\n"
                f"View the listing and upload your title deed:\n{ctx['listing_url']}\n\n"
                f"Your user ID (for your records) is on Profile:\n{ctx['profile_url']}\n\n"
                f" -  Yallastay"
            ),
            template_key="listing_owner_linked",
        )
    except Exception:
        logger.exception(
            "listing_owner_linked failed owner_id=%s listing_id=%s",
            owner.pk,
            listing.pk,
        )


def send_owner_invite_email(
    *,
    to_email: str,
    listing: Listing,
    realtor,
    invite_token: str,
) -> None:
    """Email a prospective landlord with signup + one-click link token."""
    title = (listing.title or "Your property")[:200]
    prop_url = _frontend_url(f"/property/{listing.pk}/")
    signup_url = (
        _frontend_url("/signup")
        + f"?role=landlord&listing_invite={invite_token}&next=/property/{listing.pk}"
    )
    accept_url = (
        _frontend_url(f"/property/{listing.pk}/")
        + f"?accept_owner_invite={invite_token}"
    )
    realtor_name = (
        (getattr(realtor, "first_name", None) or "").strip()
        or getattr(realtor, "email", "")
        or "Your realtor"
    )
    ctx = {
        "listing_title": title,
        "realtor_name": realtor_name,
        "listing_url": prop_url,
        "signup_url": signup_url,
        "accept_url": accept_url,
    }
    try:
        send_transactional_email_from_template(
            to_email,
            "listing_owner_invite",
            ctx,
        )
    except ValueError:
        send_transactional_email(
            to_email,
            subject=f"{realtor_name} invited you as owner - {title}",
            body_text=(
                f"Hi,\n\n"
                f"{realtor_name} listed “{title}” for you on Yallastay.\n\n"
                f"1) Create a landlord account (or sign in):\n{signup_url}\n\n"
                f"2) After signup, open the listing and tap “Accept owner link” - "
                f"or we link you automatically when you register with the link above.\n\n"
                f"View the listing:\n{prop_url}\n\n"
                f" -  Yallastay"
            ),
            template_key="listing_owner_invite",
        )
    except Exception:
        logger.exception(
            "listing_owner_invite failed listing_id=%s email=%s",
            listing.pk,
            to_email,
        )
