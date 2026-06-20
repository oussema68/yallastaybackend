from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile, LandlordProfile, RealtorProfile
from accounts.tokens import email_verification_token_generator
from emails.models import EmailMessage

User = get_user_model()


class AuthViewTests(APITestCase):
    def test_register(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "test@example.com",
                "password": "TestPass123!",
                "role": "tenant",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "test@example.com")
        self.assertFalse(response.data["user"]["profile"]["is_email_verified"])
        self.assertTrue(
            UserProfile.objects.filter(user__email="test@example.com").exists()
        )
        self.assertEqual(response.data["user"]["profile"]["role"], "tenant")

    def test_register_validation_short_password(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "test@example.com",
                "password": "short",
                "role": "tenant",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        User.objects.create_user(email="dup@example.com", password="Pass123!")
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "dup@example.com",
                "password": "TestPass123!",
                "role": "tenant",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_as_landlord_creates_landlord_profile(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "landlord@example.com",
                "password": "TestPass123!",
                "role": "landlord",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="landlord@example.com")
        self.assertTrue(LandlordProfile.objects.filter(user=user).exists())

    def test_register_as_realtor_creates_realtor_profile(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "realtor@example.com",
                "password": "TestPass123!",
                "role": "realtor",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="realtor@example.com")
        self.assertTrue(RealtorProfile.objects.filter(user=user).exists())

    def test_login(self):
        User.objects.create_user(email="login@example.com", password="Pass123!")
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "login@example.com",
                "password": "Pass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_login_wrong_password(self):
        User.objects.create_user(email="login@example.com", password="Pass123!")
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "login@example.com",
                "password": "WrongPass!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "nope@example.com",
                "password": "Pass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_auth(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_authenticated(self):
        user = User.objects.create_user(email="me@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant")
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@example.com")
        self.assertIn("is_staff", response.data)
        self.assertIs(response.data["is_staff"], False)
        self.assertIn("is_superuser", response.data)
        self.assertIs(response.data["is_superuser"], False)
        self.assertIn("profile", response.data)
        self.assertIn("can_verify_documents", response.data["profile"])
        self.assertIs(response.data["profile"]["can_verify_documents"], False)

    def test_me_includes_is_staff_true(self):
        user = User.objects.create_user(
            email="staffme@example.com", password="Pass123!", is_staff=True
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIs(response.data["is_staff"], True)

    def test_me_realtor_includes_realtor_profile(self):
        user = User.objects.create_user(email="relme@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="realtor")
        RealtorProfile.objects.create(user=user, agency_name="Test Agency")
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rp = response.data["realtor_profile"]
        self.assertIsNotNone(rp)
        self.assertFalse(rp["is_approved"])
        self.assertFalse(rp["license_document_uploaded"])

    def test_me_landlord_has_null_realtor_profile(self):
        user = User.objects.create_user(email="llme@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="landlord")
        LandlordProfile.objects.create(user=user)
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["realtor_profile"])
        lp = response.data["landlord_profile"]
        self.assertIsNotNone(lp)
        self.assertFalse(lp["is_approved"])

    def test_me_update_profile(self):
        user = User.objects.create_user(email="me@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant")
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            "/api/auth/me/", {"phone": "+971501234567"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.phone, "+971501234567")

    def test_me_update_renter_optional_search_fields(self):
        user = User.objects.create_user(email="renter@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant")
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            "/api/auth/me/",
            {
                "place_of_work_or_studies": "ACME LLC / University of X",
                "sex": "female",
                "age": 24,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.profile.refresh_from_db()
        self.assertEqual(
            user.profile.place_of_work_or_studies, "ACME LLC / University of X"
        )
        self.assertEqual(user.profile.sex, "female")
        self.assertEqual(user.profile.age, 24)
        self.assertEqual(response.data["profile"]["age"], 24)

    def test_logout(self):
        user = User.objects.create_user(email="logout@example.com", password="Pass123!")
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        response = self.client.post(
            "/api/auth/logout/", {"refresh": str(refresh)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_refresh_token(self):
        user = User.objects.create_user(
            email="refresh@example.com", password="Pass123!"
        )
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        response = self.client.post(
            "/api/auth/refresh/", {"refresh": str(refresh)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@test.com",
    )
    def test_register_queues_verification_email_when_configured(self):
        before = EmailMessage.objects.count()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/auth/register/",
                {
                    "email": "verifyflow@example.com",
                    "password": "TestPass123!",
                    "role": "tenant",
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EmailMessage.objects.count(), before + 1)
        last = EmailMessage.objects.order_by("-id").first()
        self.assertEqual(last.template_key, "email_verification")
        self.assertEqual(last.to_email, "verifyflow@example.com")

    def test_verify_email_success(self):
        user = User.objects.create_user(email="v@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant")
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token_generator.make_token(user)
        response = self.client.get(f"/api/auth/verify-email/{uidb64}/{token}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "Email verified.")
        self.assertTrue(response.data["user"]["profile"]["is_email_verified"])
        user.profile.refresh_from_db()
        self.assertTrue(user.profile.is_email_verified)

    def test_verify_email_query_string_success(self):
        user = User.objects.create_user(email="query@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant")
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token_generator.make_token(user)
        response = self.client.get(
            "/api/auth/verify-email/",
            {"uid": uidb64, "token": token},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "Email verified.")

    def test_verify_email_invalid_token(self):
        user = User.objects.create_user(email="bad@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant")
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.get(f"/api/auth/verify-email/{uidb64}/wrong-token/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_email_second_request_returns_already_verified(self):
        user = User.objects.create_user(email="reuse@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant")
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token_generator.make_token(user)
        url = f"/api/auth/verify-email/{uidb64}/{token}/"
        r1 = self.client.get(url)
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        r2 = self.client.get(url)
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.data["detail"], "Email already verified.")

    def test_verify_email_redirect_when_already_verified(self):
        user = User.objects.create_user(email="done@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant", is_email_verified=True)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token_generator.make_token(user)
        response = self.client.get(
            f"/api/auth/verify-email/{uidb64}/{token}/?redirect=1"
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_resend_verification_requires_auth(self):
        response = self.client.post("/api/auth/verify-email/resend/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@test.com",
    )
    def test_resend_verification_sends_email(self):
        user = User.objects.create_user(email="resend@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant")
        self.client.force_authenticate(user=user)
        before = EmailMessage.objects.count()
        response = self.client.post("/api/auth/verify-email/resend/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(EmailMessage.objects.count(), before + 1)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@test.com",
    )
    def test_resend_verification_when_already_verified(self):
        user = User.objects.create_user(email="ok@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant", is_email_verified=True)
        self.client.force_authenticate(user=user)
        before = EmailMessage.objects.count()
        response = self.client.post("/api/auth/verify-email/resend/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(EmailMessage.objects.count(), before)
