import os
from unittest.mock import patch

from django.test import TestCase

from sms.models import SmsMessage


class TwilioWebhookTests(TestCase):
    def test_status_webhook_updates_message(self):
        msg = SmsMessage.objects.create(
            to_number="+971501234567",
            body="x",
            provider_message_id="SM123",
            status=SmsMessage.STATUS_SENT,
        )
        with patch.dict(os.environ, {"TWILIO_WEBHOOK_INSECURE_OK": "true"}):
            response = self.client.post(
                "/api/sms/webhooks/twilio/status/",
                {"MessageSid": "SM123", "MessageStatus": "delivered"},
            )
        self.assertEqual(response.status_code, 200)
        msg.refresh_from_db()
        self.assertEqual(msg.status, SmsMessage.STATUS_DELIVERED)

    def test_webhook_rejects_without_dev_or_signature(self):
        with patch.dict(
            os.environ,
            {"TWILIO_WEBHOOK_INSECURE_OK": "false", "TWILIO_AUTH_TOKEN": ""},
            clear=False,
        ):
            response = self.client.post(
                "/api/sms/webhooks/twilio/status/",
                {"MessageSid": "SM999", "MessageStatus": "delivered"},
            )
        self.assertEqual(response.status_code, 403)
