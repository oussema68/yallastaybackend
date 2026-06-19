from django.contrib.auth import get_user_model
from django.test import TestCase

from emails.models import EmailMessage, EmailTemplate

User = get_user_model()


class EmailMessageModelTests(TestCase):
    def test_create_minimal(self):
        m = EmailMessage.objects.create(
            to_email="u@example.com", subject="Hi", status=EmailMessage.STATUS_QUEUED
        )
        self.assertEqual(m.status, EmailMessage.STATUS_QUEUED)

    def test_user_fk_optional(self):
        u = User.objects.create_user(email="a@b.com", password="x")
        m = EmailMessage.objects.create(to_email="x@y.com", user=u)
        self.assertEqual(m.user_id, u.id)


class EmailTemplateModelTests(TestCase):
    def test_create_template(self):
        t = EmailTemplate.objects.create(
            key="k1",
            name="N",
            subject="S",
            body_text="B",
        )
        self.assertEqual(str(t), "N (k1)")
