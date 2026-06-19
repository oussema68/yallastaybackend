"""
Helper to create in-app notifications. Call from listings, bookings, messaging, etc.

Copy here is short UI text - not the same as email bodies (see NOTIFICATIONS.md).
"""

from __future__ import annotations

from .models import Notification, NotificationPreference


def _in_app_enabled(user, notification_type: str) -> bool:
    """Respect per-type in-app preference; default on if no row exists."""
    pref = NotificationPreference.objects.filter(
        user=user, channel="in_app", notification_type=notification_type
    ).first()
    if pref is None:
        return True
    return pref.enabled


def notify_user(user, notification_type, title, body="", *, link=""):
    """
    Create an in-app notification for a user.

    Skips creation if the user disabled in-app for this ``notification_type``
    (channel ``in_app`` in NotificationPreference).

    ``link`` should be a frontend path (e.g. ``/dashboard``) or full URL; the client
    uses it for navigation when the user taps the notification.
    """
    if not _in_app_enabled(user, notification_type):
        return None
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        link=(link or "").strip()[:500],
    )
