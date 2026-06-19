from django.contrib.auth import get_user_model
from django.test import TestCase

from sms.models import SmsMessage, SmsTemplate

User = get_user_model()


class SmsMessageModelTests(TestCase):
    def test_create_minimal(self):
        m = SmsMessage.objects.create(
            to_number="+971501234567", body="hi", status=SmsMessage.STATUS_QUEUED
        )
        self.assertEqual(m.status, SmsMessage.STATUS_QUEUED)
        self.assertEqual(m.retry_count, 0)

    def test_user_fk_optional(self):
        u = User.objects.create_user(email="a@b.com", password="x")
        m = SmsMessage.objects.create(to_number="+971500000000", user=u)
        self.assertEqual(m.user_id, u.id)


class SmsTemplateModelTests(TestCase):
    def test_create_template(self):
        t = SmsTemplate.objects.create(
            key="t1",
            name="T",
            body="Hello {name}",
        )
        self.assertEqual(str(t), "T (t1)")
