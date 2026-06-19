"""Owner ↔ realtor listing assignment helpers."""

from __future__ import annotations

from django.contrib.auth import get_user_model

User = get_user_model()


def user_role(user) -> str | None:
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.profile.role
    except Exception:
        return None


def is_landlord_user(user) -> bool:
    return user_role(user) == "landlord"


def is_realtor_user(user) -> bool:
    return user_role(user) == "realtor"


def reviewing_broker_user(listing):
    """
    Realtor who reviews owner documents and may add Trakheesi on owner-listed units.
    Prefer explicit ``assigned_realtor``; else the listing publisher when they are a realtor.
    """
    if listing.assigned_realtor_id:
        return listing.assigned_realtor
    if listing.listed_by_id and is_realtor_user(listing.listed_by):
        return listing.listed_by
    return None


def reviewing_broker_id(listing) -> int | None:
    broker = reviewing_broker_user(listing)
    return broker.id if broker else None


def user_is_reviewing_broker(user, listing) -> bool:
    bid = reviewing_broker_id(listing)
    return bid is not None and bid == getattr(user, "id", None)


def validate_property_owner_target(owner_user) -> None:
    from rest_framework import serializers

    if owner_user is None:
        return
    if not is_landlord_user(owner_user):
        raise serializers.ValidationError(
            {
                "property_owner": (
                    "The property owner must be a registered landlord account. "
                    "Ask them to sign up as a landlord and share their user ID from Profile."
                )
            }
        )


def reset_owner_verification_state(listing_pk: int) -> None:
    from .models import Listing

    Listing.objects.filter(pk=listing_pk).update(
        owner_verification_status="none",
        owner_verification_note="",
        owner_verification_by_id=None,
        owner_verification_at=None,
    )
