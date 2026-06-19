import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from sms.models import SmsMessage, SmsTemplate
from sms.services import send_sms, send_sms_from_template

User = get_user_model()


class SendSmsTests(TestCase):
    def test_skipped_without_twilio_env(self):
        with patch.dict(
            os.environ,
            {
                "TWILIO_ACCOUNT_SID": "",
                "TWILIO_AUTH_TOKEN": "",
                "TWILIO_FROM_NUMBER": "",
            },
            clear=False,
        ):
            m = send_sms("+971501234567", body="test")
        m.refresh_from_db()
        self.assertEqual(m.status, SmsMessage.STATUS_SKIPPED)
        self.assertIn("Twilio env not configured", m.error_message)

    def test_send_from_template_skipped_without_twilio(self):
        SmsTemplate.objects.create(
            key="test_sms_tpl",
            name="Test",
            body="Code: {code}",
            is_active=True,
        )
        with patch.dict(
            os.environ,
            {
                "TWILIO_ACCOUNT_SID": "",
                "TWILIO_AUTH_TOKEN": "",
                "TWILIO_FROM_NUMBER": "",
            },
            clear=False,
        ):
            m = send_sms_from_template(
                "+971501234567", "test_sms_tpl", {"code": "123456"}
            )
        m.refresh_from_db()
        self.assertEqual(m.body, "Code: 123456")
        self.assertEqual(m.template_key, "test_sms_tpl")
        self.assertEqual(m.status, SmsMessage.STATUS_SKIPPED)

    def test_send_from_template_missing_raises(self):
        with self.assertRaises(ValueError):
            send_sms_from_template("+971501234567", "missing_key")

    @override_settings(DEBUG=True)
    def test_dev_outbound_log_when_debug_true(self):
        with patch.dict(
            os.environ,
            {
                "TWILIO_ACCOUNT_SID": "",
                "TWILIO_AUTH_TOKEN": "",
                "TWILIO_FROM_NUMBER": "",
            },
            clear=False,
        ):
            with patch("sms.services.logger") as mock_logger:
                send_sms("+971501234567", body="hello sms")
        outbound = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "[OUTBOUND SMS]" in c.args[0]
        ]
        self.assertEqual(len(outbound), 1)

    @override_settings(DEBUG=False)
    def test_dev_outbound_log_suppressed_when_debug_false(self):
        with patch.dict(
            os.environ,
            {
                "TWILIO_ACCOUNT_SID": "",
                "TWILIO_AUTH_TOKEN": "",
                "TWILIO_FROM_NUMBER": "",
            },
            clear=False,
        ):
            with patch("sms.services.logger") as mock_logger:
                send_sms("+971501234567", body="hello sms")
        outbound = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "[OUTBOUND SMS]" in c.args[0]
        ]
        self.assertEqual(len(outbound), 0)
