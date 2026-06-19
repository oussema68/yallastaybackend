from rest_framework import permissions


def is_listing_owner(user, listing):
    """Check if user is the one who listed the property (landlord or realtor)."""
    return listing.listed_by == user


class CanManageViewing(permissions.BasePermission):
    """User can confirm/reject if they listed the property."""

    def has_object_permission(self, request, view, obj):
        if view.action not in ["partial_update", "update"]:
            return True
        return is_listing_owner(request.user, obj.listing)
