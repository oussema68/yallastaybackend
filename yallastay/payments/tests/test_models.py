from django.contrib.auth import get_user_model
from django.test import TestCase

from payments.models import Payment

User = get_user_model()


class PaymentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )

    def test_create_payment(self):
        pmt = Payment.objects.create(
            user=self.user,
            amount=5000,
            payment_type="fee",
            currency="AED",
            status="pending",
            transaction_id="ys_abc123",
        )
        self.assertEqual(pmt.status, "pending")
        self.assertEqual(pmt.amount, 5000)
