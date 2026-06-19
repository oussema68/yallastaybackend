"""Password reset request + confirm (email template + token validation)."""

from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from accounts.models import User
from accounts.password_reset import password_reset_token_generator
from emails.models import EmailMessage


class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_password_reset_request_sends_email_when_user_exists(self):
        user = User.objects.create_user(
            email="reset@example.com", password="OldPass123!"
        )
        response = self.client.post(
            "/api/auth/password-reset/",
            {"email": "reset@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("detail", response.data)
        last = EmailMessage.objects.order_by("-id").first()
        self.assertIsNotNone(last)
        self.assertEqual(last.template_key, "password_reset")
        self.assertEqual(last.to_email, user.email)

    def test_password_reset_request_same_response_for_unknown_email(self):
        response = self.client.post(
            "/api/auth/password-reset/",
            {"email": "nobody@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        detail = response.data["detail"]
        self.assertIn("account exists", detail.lower())

    def test_password_reset_confirm_success(self):
        user = User.objects.create_user(email="ok@example.com", password="OldPass123!")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = password_reset_token_generator.make_token(user)
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "uid": uid,
                "token": token,
                "new_password": "BrandNewPass456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("BrandNewPass456!"))
        login = self.client.post(
            "/api/auth/login/",
            {"email": "ok@example.com", "password": "BrandNewPass456!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", login.data)

    def test_password_reset_confirm_rejects_bad_token(self):
        user = User.objects.create_user(email="bad@example.com", password="OldPass123!")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "uid": uid,
                "token": "invalid-token",
                "new_password": "BrandNewPass456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
