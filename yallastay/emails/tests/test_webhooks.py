import json
import os
from unittest.mock import patch

from django.test import TestCase

from emails.models import EmailMessage


class SendGridWebhookTests(TestCase):
    def test_events_updates_status_with_insecure_ok(self):
        msg = EmailMessage.objects.create(
            to_email="user@example.com",
            subject="s",
            provider_message_id="sg-msg-1",
            status=EmailMessage.STATUS_SENT,
        )
        payload = [
            {
                "event": "delivered",
                "email": "user@example.com",
                "sg_message_id": "sg-msg-1",
            }
        ]
        with patch.dict(os.environ, {"SENDGRID_WEBHOOK_INSECURE_OK": "true"}):
            response = self.client.post(
                "/api/emails/webhooks/sendgrid/events/",
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        msg.refresh_from_db()
        self.assertEqual(msg.status, EmailMessage.STATUS_DELIVERED)

    def test_rejects_without_secret_or_insecure(self):
        with patch.dict(
            os.environ, {"SENDGRID_WEBHOOK_INSECURE_OK": "false"}, clear=False
        ):
            response = self.client.post(
                "/api/emails/webhooks/sendgrid/events/",
                data="[]",
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 403)
