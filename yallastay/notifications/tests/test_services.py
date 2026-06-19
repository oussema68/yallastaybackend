from django.contrib.auth import get_user_model
from django.test import TestCase

from notifications.models import Notification, NotificationPreference
from notifications.services import notify_user

User = get_user_model()


class NotifyUserServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@example.com", password="Pass123!")

    def test_notify_user_creates_notification(self):
        n = notify_user(self.user, "general", "Hello", "World")
        self.assertIsNotNone(n)
        self.assertEqual(n.title, "Hello")
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    def test_notify_user_skips_when_in_app_disabled(self):
        NotificationPreference.objects.create(
            user=self.user,
            channel="in_app",
            notification_type="listing",
            enabled=False,
        )
        n = notify_user(self.user, "listing", "T", "B")
        self.assertIsNone(n)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 0)

    def test_notify_user_default_when_no_preference(self):
        n = notify_user(self.user, "listing", "T", "B")
        self.assertIsNotNone(n)

    def test_notify_user_stores_link(self):
        n = notify_user(self.user, "welcome", "Hi", "Body", link="/dashboard")
        self.assertEqual(n.link, "/dashboard")
