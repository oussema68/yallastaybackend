"""System user used to post official Yallastay messages in conversations."""

from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.models import UserProfile

User = get_user_model()


def get_or_create_yallastay_team_user():
    """
    Lazily create a non-login user that represents the Yallastay team in threads.
    Email is configurable via YALLASTAY_TEAM_USER_EMAIL (must not collide with real signups).
    """
    email = getattr(
        settings,
        "YALLASTAY_TEAM_USER_EMAIL",
        "yallastay-team@internal.yallastay",
    )
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "first_name": "Yallastay",
            "last_name": "Team",
            "is_active": True,
        },
    )
    if not user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=["password"])
    UserProfile.objects.get_or_create(
        user=user,
        defaults={"role": "tenant"},
    )
    return user


def is_yallastay_team_user(user) -> bool:
    if not user or not getattr(user, "email", None):
        return False
    team_email = getattr(
        settings,
        "YALLASTAY_TEAM_USER_EMAIL",
        "yallastay-team@internal.yallastay",
    )
    return user.email == team_email
