"""DRF permission for Yallastay verification staff (brokers + owners)."""

from rest_framework.permissions import BasePermission


def user_can_access_staff_verification(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    try:
        return bool(user.profile.can_verify_documents)
    except Exception:
        return False


class IsVerificationStaff(BasePermission):
    """Django staff/superuser or ``UserProfile.can_verify_documents``."""

    message = "Verification console access only."

    def has_permission(self, request, view):
        return user_can_access_staff_verification(request.user)
