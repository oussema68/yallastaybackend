from rest_framework import permissions


class IsLandlordOrRealtor(permissions.BasePermission):
    """Only landlords and approved realtors can create/edit listings."""

    def has_permission(self, request, view):
        if view.action in ["list", "retrieve"]:
            return True
        if not request.user.is_authenticated:
            return False
        from accounts.models import UserProfile, RealtorProfile

        try:
            role = request.user.profile.role
            if role == "landlord":
                return True
            if role == "realtor":
                try:
                    return request.user.realtor_profile.is_approved
                except RealtorProfile.DoesNotExist:
                    return False
            return False
        except (UserProfile.DoesNotExist, AttributeError):
            return False

    def has_object_permission(self, request, view, obj):
        if view.action in ["retrieve"]:
            return True
        if not hasattr(obj, "listed_by"):
            return False
        if obj.listed_by == request.user:
            return True
        uid = request.user.id
        # Property owner (realtor-listed unit) may PATCH title deed fields - enforced in the view.
        if (
            view.action in ("update", "partial_update")
            and getattr(obj, "property_owner_id", None) == uid
        ):
            return True
        if (
            view.action == "request_owner_verification"
            and getattr(obj, "property_owner_id", None) == uid
        ):
            return True
        if (
            view.action
            in (
                "approve_owner_verification",
                "reject_owner_verification",
            )
            and getattr(obj, "assigned_realtor_id", None) == uid
        ):
            return True
        # Assigned broker may PATCH Trakheesi permit on owner-listed units (field-level rules in the view).
        if (
            view.action == "partial_update"
            and getattr(obj, "assigned_realtor_id", None) == uid
        ):
            return True
        return False
