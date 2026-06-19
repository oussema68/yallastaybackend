import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from core.models import Area, University
from emails.models import EmailMessage, EmailTemplate
from sms.models import SmsMessage, SmsTemplate


class SeedCoreCommandTests(TestCase):
    def test_seed_core(self):
        out = StringIO()
        call_command("seed_core", stdout=out)
        self.assertGreater(Area.objects.count(), 0)
        self.assertGreater(University.objects.count(), 0)
        self.assertIn("Seeded", out.getvalue())


class OutboundSmokeCommandTests(TestCase):
    def setUp(self):
        EmailTemplate.objects.update_or_create(
            key="welcome",
            defaults={
                "name": "Welcome",
                "subject": "Welcome {first_name}",
                "body_text": "Hi {first_name} - {email}",
                "body_html": "",
                "is_active": True,
            },
        )
        SmsTemplate.objects.update_or_create(
            key="generic_message",
            defaults={
                "name": "Generic",
                "body": "Yallastay: {message}",
                "is_active": True,
            },
        )

    @override_settings(
        DEBUG=True,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@test.com",
    )
    def test_outbound_smoke_creates_email_and_sms_rows(self):
        before_e = EmailMessage.objects.count()
        before_s = SmsMessage.objects.count()
        with patch.dict(
            os.environ,
            {
                "TWILIO_ACCOUNT_SID": "",
                "TWILIO_AUTH_TOKEN": "",
                "TWILIO_FROM_NUMBER": "",
            },
            clear=False,
        ):
            out = StringIO()
            call_command(
                "outbound_smoke",
                email="smoke@test.com",
                phone="+971501111111",
                stdout=out,
            )
        text = out.getvalue()
        self.assertIn("EmailMessage id=", text)
        self.assertIn("SmsMessage id=", text)
        self.assertIn("Done", text)
        self.assertEqual(EmailMessage.objects.count(), before_e + 1)
        self.assertEqual(SmsMessage.objects.count(), before_s + 1)
        last_email = EmailMessage.objects.order_by("-id").first()
        last_sms = SmsMessage.objects.order_by("-id").first()
        self.assertEqual(last_email.to_email, "smoke@test.com")
        self.assertEqual(last_sms.to_number, "+971501111111")
        self.assertEqual(last_email.status, EmailMessage.STATUS_SENT)
        self.assertEqual(last_sms.status, SmsMessage.STATUS_SKIPPED)
