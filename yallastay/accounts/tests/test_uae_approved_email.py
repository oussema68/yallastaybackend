from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from accounts.models import UAEIDVerification, UserProfile
from emails.models import EmailMessage

User = get_user_model()


class UAEApprovedEmailTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.com",
    )
    def test_email_sent_when_uae_flips_to_approved(self):
        user = User.objects.create_user(email="u@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant")
        v = UAEIDVerification.objects.create(
            user=user, id_hash="abc123hash", status="pending"
        )
        before = EmailMessage.objects.count()
        v.status = "approved"
        v.save()
        self.assertEqual(EmailMessage.objects.count() - before, 1)
        msg = EmailMessage.objects.latest("id")
        self.assertEqual(msg.template_key, "uae_id_approved_user")
        self.assertEqual(msg.to_email, user.email)
        self.assertIn("approved", msg.body_text.lower())

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.com",
    )
    def test_no_email_when_already_approved(self):
        user = User.objects.create_user(email="u2@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant")
        v = UAEIDVerification.objects.create(
            user=user, id_hash="def456hash", status="approved"
        )
        before = EmailMessage.objects.count()
        v.document = None
        v.save()
        self.assertEqual(EmailMessage.objects.count() - before, 0)
