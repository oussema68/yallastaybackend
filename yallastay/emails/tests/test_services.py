from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from emails.models import EmailMessage, EmailTemplate
from emails.services import (
    send_transactional_email,
    send_transactional_email_from_template,
)

User = get_user_model()


class SendTransactionalEmailTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@test.com",
    )
    def test_sends_with_locmem(self):
        m = send_transactional_email(
            "dest@example.com",
            subject="Hello",
            body_text="Body",
        )
        m.refresh_from_db()
        self.assertEqual(m.status, EmailMessage.STATUS_SENT)
        self.assertEqual(m.to_email, "dest@example.com")

    @override_settings(DEFAULT_FROM_EMAIL="")
    def test_skipped_without_from_email(self):
        m = send_transactional_email("a@b.com", subject="S")
        m.refresh_from_db()
        self.assertEqual(m.status, EmailMessage.STATUS_SKIPPED)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@test.com",
    )
    def test_send_from_template(self):
        EmailTemplate.objects.create(
            key="test_tpl",
            name="Test",
            subject="Hello {name}",
            body_text="Hi {name}",
            body_html="<p>Hi {name}</p>",
            is_active=True,
        )
        m = send_transactional_email_from_template(
            "x@y.com",
            "test_tpl",
            {"name": "Sam"},
        )
        m.refresh_from_db()
        self.assertEqual(m.status, EmailMessage.STATUS_SENT)
        self.assertEqual(m.subject, "Hello Sam")
        self.assertIn("Hi Sam", m.body_text)
        self.assertEqual(m.template_key, "test_tpl")

    def test_send_from_template_missing_raises(self):
        with self.assertRaises(ValueError):
            send_transactional_email_from_template("a@b.com", "nonexistent")

    @override_settings(
        DEBUG=True,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@test.com",
    )
    def test_dev_outbound_log_when_debug_true(self):
        with patch("emails.services.logger") as mock_logger:
            send_transactional_email(
                "dest@example.com",
                subject="Subj",
                body_text="Body text",
            )
        outbound = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "[OUTBOUND EMAIL]" in c.args[0]
        ]
        self.assertEqual(len(outbound), 1)

    @override_settings(
        DEBUG=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@test.com",
    )
    def test_dev_outbound_log_suppressed_when_debug_false(self):
        with patch("emails.services.logger") as mock_logger:
            send_transactional_email(
                "dest@example.com",
                subject="Subj",
                body_text="Body text",
            )
        outbound = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "[OUTBOUND EMAIL]" in c.args[0]
        ]
        self.assertEqual(len(outbound), 0)
