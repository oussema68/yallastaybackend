"""Transactional emails when a user publishes a listing."""

from __future__ import annotations

import logging

from django.conf import settings

from emails.services import send_transactional_email_from_template

from .models import Listing

logger = logging.getLogger(__name__)


def send_listing_created_email(
    user, listing: Listing, *, is_first: bool | None = None
) -> None:
    """
    Notify the lister that their property was added (email).

    Uses ``listing_created_first`` when this is the only listing for that user
    (counted per ``listed_by``), otherwise ``listing_created``.
    Pass ``is_first`` to avoid an extra count query when already computed upstream.

    Does not raise on failure (logs instead).
    """
    if is_first is None:
        total_for_user = Listing.objects.filter(listed_by=user).count()
        is_first = total_for_user == 1
    template_key = "listing_created_first" if is_first else "listing_created"

    first = (getattr(user, "first_name", None) or "").strip() or "there"
    base = (getattr(settings, "FRONTEND_URL", None) or "").rstrip("/")
    listing_url = f"{base}/property/{listing.pk}" if base else f"/property/{listing.pk}"

    ctx = {
        "first_name": first,
        "listing_title": listing.title,
        "listing_id": listing.pk,
        "listing_url": listing_url,
    }
    try:
        send_transactional_email_from_template(
            user.email,
            template_key,
            ctx,
            user=user,
        )
    except ValueError as e:
        logger.warning("%s template: %s", template_key, e)
    except Exception:
        logger.exception(
            "%s failed user_id=%s listing_id=%s", template_key, user.pk, listing.pk
        )
