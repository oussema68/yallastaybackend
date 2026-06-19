from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile, UAEIDVerification, UniversityVerification
from core.models import University
from emails.models import EmailMessage

User = get_user_model()


class VerificationViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        self.university = University.objects.create(
            name="UAE University", domain="uaeu.ac.ae"
        )

    def test_verification_status_requires_auth(self):
        response = self.client.get("/api/verification/status/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verification_status_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/verification/status/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("uae_id_verified", response.data)
        self.assertIn("university_verified", response.data)

    def test_uae_id_submit_requires_auth(self):
        response = self.client.post(
            "/api/verification/uae-id/",
            {
                "emirates_id": "784-1234-1234567-1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_uae_id_submit_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/verification/uae-id/",
            {
                "emirates_id": "784-1234-1234567-1",
            },
            format="json",
        )
        self.assertIn(
            response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED)
        )
        self.assertTrue(UAEIDVerification.objects.filter(user=self.user).exists())

    def test_uae_id_invalid_format(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/verification/uae-id/",
            {
                "emirates_id": "123",  # Too short
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_university_submit_requires_auth(self):
        response = self.client.post(
            "/api/verification/university/",
            {
                "email": "student@uaeu.ac.ae",
                "university_id": self.university.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_university_submit_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/verification/university/",
            {
                "email": "student@uaeu.ac.ae",
                "university_id": self.university.id,
                "student_id": "12345",
            },
            format="json",
        )
        self.assertIn(
            response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED)
        )
        self.assertTrue(UniversityVerification.objects.filter(user=self.user).exists())

    def test_university_submit_wrong_domain(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/verification/university/",
            {
                "email": "student@gmail.com",
                "university_id": self.university.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.com",
        VERIFICATION_TEAM_EMAIL="verify-team@example.com",
    )
    def test_uae_id_submit_sends_user_and_team_emails(self):
        self.client.force_authenticate(user=self.user)
        before = EmailMessage.objects.count()
        response = self.client.post(
            "/api/verification/uae-id/",
            {
                "emirates_id": "784-1234-1234567-1",
            },
            format="json",
        )
        self.assertIn(
            response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED)
        )
        self.assertEqual(EmailMessage.objects.count(), before + 2)
        self.assertTrue(
            EmailMessage.objects.filter(
                to_email=self.user.email, template_key="uae_id_submitted_user"
            ).exists()
        )
        self.assertTrue(
            EmailMessage.objects.filter(
                to_email="verify-team@example.com",
                template_key="uae_id_submitted_team",
            ).exists()
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.com",
        VERIFICATION_TEAM_EMAIL="",
    )
    def test_uae_id_submit_sends_user_email_when_team_not_configured(self):
        self.client.force_authenticate(user=self.user)
        before = EmailMessage.objects.count()
        response = self.client.post(
            "/api/verification/uae-id/",
            {
                "emirates_id": "784-1234-1234567-1",
            },
            format="json",
        )
        self.assertIn(
            response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED)
        )
        self.assertEqual(EmailMessage.objects.count(), before + 1)
        self.assertTrue(
            EmailMessage.objects.filter(
                to_email=self.user.email, template_key="uae_id_submitted_user"
            ).exists()
        )
