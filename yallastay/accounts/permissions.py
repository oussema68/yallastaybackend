from rest_framework import permissions


def user_has_uae_id_verified(user):
    """Check if user has approved UAE ID verification (required for viewings, reservations)."""
    if not user or not user.is_authenticated:
        return False
    try:
        v = user.uae_id_verification
        return v.status == "approved"
    except Exception:
        return False


class IsUAEIDVerified(permissions.BasePermission):
    """Require UAE ID verification. Return 403 with message if not verified."""

    message = "UAE ID verification is required for this action."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return user_has_uae_id_verified(request.user)
