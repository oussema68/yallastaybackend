from rest_framework import permissions


class IsRealtorOrLandlord(permissions.BasePermission):
    """
    Realtors: full platform analytics.
    Landlords: only their own listings (my-listings-insights only; renter-demographics and popular-areas are platform-wide for realtors).
    """

    message = "Analytics are available to realtors and landlords only."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        from accounts.models import UserProfile

        try:
            role = request.user.profile.role
            return role in ["realtor", "landlord"]
        except (UserProfile.DoesNotExist, AttributeError):
            return False


class IsRealtor(permissions.BasePermission):
    """Realtors only (for platform-wide analytics)."""

    message = "This analytics endpoint is available to realtors only."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        from accounts.models import UserProfile, RealtorProfile

        try:
            if request.user.profile.role != "realtor":
                return False
            return request.user.realtor_profile.is_approved
        except (UserProfile.DoesNotExist, RealtorProfile.DoesNotExist, AttributeError):
            return False
