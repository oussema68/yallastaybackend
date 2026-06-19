from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from notifications.models import Notification

User = get_user_model()


class NotificationViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )

    def test_list_notifications_requires_auth(self):
        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_notifications_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mark_notification_read(self):
        n = Notification.objects.create(
            user=self.user, notification_type="booking", title="Test", body="Body"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(f"/api/notifications/{n.id}/read/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        n.refresh_from_db()
        self.assertTrue(n.read)

    def test_get_notification_preferences(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/notifications/preferences/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_notification_preferences(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            "/api/notifications/preferences/",
            {
                "channel": "email",
                "notification_type": "general",
                "enabled": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
