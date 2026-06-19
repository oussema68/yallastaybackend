from django.contrib.auth import get_user_model
from django.test import TestCase

from notifications.models import Notification, NotificationPreference

User = get_user_model()


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )

    def test_create_notification(self):
        n = Notification.objects.create(
            user=self.user,
            notification_type="booking",
            title="Viewing confirmed",
            body="Your viewing is confirmed",
        )
        self.assertFalse(n.read)
        self.assertEqual(str(n), f"{self.user.email} - Viewing confirmed")


class NotificationPreferenceModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )

    def test_create_preference(self):
        pref = NotificationPreference.objects.create(
            user=self.user, channel="email", notification_type="general", enabled=True
        )
        self.assertTrue(pref.enabled)
