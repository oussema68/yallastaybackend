"""Auth endpoints use ScopedRateThrottle with dedicated scopes (see settings REST_FRAMEWORK)."""

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from accounts.models import User
from accounts.views import (
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendVerificationEmailView,
    ThrottledTokenRefreshView,
    VerifyEmailView,
)


class AuthThrottleConfigTests(TestCase):
    """Smoke-test that views declare scopes matching DEFAULT_THROTTLE_RATES keys."""

    def test_scopes_registered_in_settings(self):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        for scope in (
            "auth_login",
            "auth_register",
            "auth_refresh",
            "auth_password_reset",
            "auth_password_reset_confirm",
            "auth_verify_email",
            "auth_resend_verification",
        ):
            with self.subTest(scope=scope):
                self.assertIn(scope, rates)

    def test_views_use_matching_scopes(self):
        self.assertEqual(LoginView.throttle_scope, "auth_login")
        self.assertEqual(ThrottledTokenRefreshView.throttle_scope, "auth_refresh")
        self.assertEqual(RegisterView.throttle_scope, "auth_register")
        self.assertEqual(PasswordResetRequestView.throttle_scope, "auth_password_reset")
        self.assertEqual(
            PasswordResetConfirmView.throttle_scope, "auth_password_reset_confirm"
        )
        self.assertEqual(VerifyEmailView.throttle_scope, "auth_verify_email")
        self.assertEqual(
            ResendVerificationEmailView.throttle_scope, "auth_resend_verification"
        )


class AuthLoginThrottleBurstTests(TestCase):
    """
    Integration: assert HTTP 429 after exceeding auth_login scope.

    DRF's `SimpleRateThrottle.THROTTLE_RATES` is bound at import time to the
    then-current `api_settings.DEFAULT_THROTTLE_RATES` dict, so `override_settings`
    alone does not change live throttle limits. For this test we temporarily
    replace the class attribute with a copy that tightens `auth_login` only.
    """

    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(email="burst@example.com", password="Pass123!")

    def test_login_returns_429_after_burst(self):
        original = SimpleRateThrottle.THROTTLE_RATES
        patched = dict(original)
        patched["auth_login"] = "2/minute"
        SimpleRateThrottle.THROTTLE_RATES = patched
        try:
            cache.clear()
            for _ in range(2):
                r = self.client.post(
                    "/api/auth/login/",
                    {"email": "burst@example.com", "password": "wrong"},
                    format="json",
                )
                self.assertEqual(r.status_code, 401)
            third = self.client.post(
                "/api/auth/login/",
                {"email": "burst@example.com", "password": "wrong"},
                format="json",
            )
            self.assertEqual(third.status_code, 429)
            self.assertIn("detail", third.data)
        finally:
            SimpleRateThrottle.THROTTLE_RATES = original
            cache.clear()
