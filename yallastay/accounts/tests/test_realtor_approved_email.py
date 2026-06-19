from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import RealtorProfile, UserProfile
from emails.models import EmailMessage

User = get_user_model()


class RealtorApprovedEmailTests(APITestCase):
    @override_settings(DEFAULT_FROM_EMAIL="noreply@example.com")
    def test_email_sent_when_realtor_flips_to_approved(self):
        user = User.objects.create_user(email="r@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="realtor")
        rp = RealtorProfile.objects.create(
            user=user, agency_name="Test Agency", is_approved=False
        )
        before = EmailMessage.objects.count()
        rp.is_approved = True
        rp.save()
        self.assertEqual(EmailMessage.objects.count() - before, 1)
        msg = EmailMessage.objects.latest("id")
        self.assertEqual(msg.template_key, "realtor_approved_user")
        self.assertEqual(msg.to_email, user.email)
        self.assertIn("approved", msg.body_text.lower())

    @override_settings(DEFAULT_FROM_EMAIL="noreply@example.com")
    def test_no_email_when_already_approved(self):
        user = User.objects.create_user(email="r2@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="realtor")
        rp = RealtorProfile.objects.create(user=user, agency_name="A", is_approved=True)
        before = EmailMessage.objects.count()
        rp.rera_number = "123"
        rp.save()
        self.assertEqual(EmailMessage.objects.count() - before, 0)
