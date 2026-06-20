from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile, LandlordProfile, UAEIDVerification
from core.models import Area
from listings.models import Listing
from bookings.models import Reservation
from lifestyle_services.models import (
    LifestylePartner,
    LifestylePlan,
    LifestyleService,
    LifestyleSubscription,
)

User = get_user_model()


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


class LifestyleViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="Desc",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )
        self.plan = LifestylePlan.objects.create(name="Essential", tier=1, price=500)
        LifestyleService.objects.create(
            plan=self.plan, service_type="cleaning", details="Weekly"
        )

    def test_list_lifestyle_plans_requires_auth(self):
        response = self.client.get("/api/lifestyle-plans/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_lifestyle_plans_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/lifestyle-plans/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_subscriptions(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/lifestyle-subscriptions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_subscription(self):
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="confirmed",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/lifestyle-subscriptions/",
            {
                "plan_id": self.plan.id,
                "reservation_id": res.id,
                "start_date": "2026-04-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("checkout_url", response.data)
        self.assertIn("subscription", response.data)
        self.assertEqual(response.data["subscription"]["status"], "pending_payment")
        self.assertEqual(
            response.data["subscription"]["latest_payment"]["status"], "pending"
        )
        sub = LifestyleSubscription.objects.get(user=self.user)
        self.assertEqual(sub.status, "pending_payment")
        tx = response.data["transaction_id"]
        self.client.post(
            "/api/payments/webhook/stub/",
            {"transaction_id": tx},
            format="json",
        )
        sub.refresh_from_db()
        self.assertEqual(sub.status, "active")

    def test_create_subscription_requires_uae_approved(self):
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="confirmed",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/lifestyle-subscriptions/",
            {
                "plan_id": self.plan.id,
                "reservation_id": res.id,
                "start_date": "2026-04-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(LifestyleSubscription.objects.filter(user=self.user).exists())

    def test_patch_cancel_pending_payment_cancels_linked_payment(self):
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="confirmed",
        )
        sub = LifestyleSubscription.objects.create(
            reservation=res,
            plan=self.plan,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="pending_payment",
        )
        from payments.models import Payment

        pay = Payment.objects.create(
            user=self.user,
            amount=self.plan.price,
            currency="AED",
            payment_type="lifestyle",
            status="pending",
            reservation=res,
            lifestyle_subscription=sub,
            transaction_id="ys_pend",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/lifestyle-subscriptions/{sub.id}/",
            {"status": "cancelled"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pay.refresh_from_db()
        self.assertEqual(pay.status, "cancelled")

    def test_subscription_detail_and_cancel(self):
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="confirmed",
        )
        sub = LifestyleSubscription.objects.create(
            reservation=res,
            plan=self.plan,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="active",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/lifestyle-subscriptions/{sub.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.patch(
            f"/api/lifestyle-subscriptions/{sub.id}/",
            {"status": "cancelled"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "cancelled")

    def test_create_subscription_completed_reservation_succeeds(self):
        """Dashboard may show 'rented' with status=completed; subscribe must still work."""
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="completed",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/lifestyle-subscriptions/",
            {
                "plan_id": self.plan.id,
                "reservation_id": res.id,
                "start_date": "2026-04-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_subscription_rejected_when_reservation_past_end_date(self):
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2024-01-01",
            end_date="2025-06-01",
            status="confirmed",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/lifestyle-subscriptions/",
            {
                "plan_id": self.plan.id,
                "reservation_id": res.id,
                "start_date": "2024-01-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(LifestyleSubscription.objects.filter(user=self.user).exists())

    def test_list_lifestyle_partners_requires_auth(self):
        response = self.client.get("/api/lifestyle-partners/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_lifestyle_partners_filter_gym(self):
        LifestylePartner.objects.create(
            partner_type="gym",
            name="Test Gym",
            area_label="Marina",
            sort_order=0,
            is_active=True,
        )
        LifestylePartner.objects.create(
            partner_type="cleaning_vendor",
            name="Clean Co",
            area_label="",
            sort_order=0,
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/lifestyle-partners/", {"partner_type": "gym"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Test Gym")

    def test_subscription_preferences_active_only(self):
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="confirmed",
        )
        sub = LifestyleSubscription.objects.create(
            reservation=res,
            plan=self.plan,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="pending_payment",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            f"/api/lifestyle-subscriptions/{sub.id}/preferences/"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        sub.status = "active"
        sub.save(update_fields=["status"])
        response = self.client.get(
            f"/api/lifestyle-subscriptions/{sub.id}/preferences/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cleaning_weekday"], "wed")

    def test_subscription_preferences_patch_gym(self):
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="confirmed",
        )
        gym = LifestylePartner.objects.create(
            partner_type="gym",
            name="Partner Gym",
            area_label="Marina",
            sort_order=0,
            is_active=True,
        )
        sub = LifestyleSubscription.objects.create(
            reservation=res,
            plan=self.plan,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="active",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/lifestyle-subscriptions/{sub.id}/preferences/",
            {
                "gym_partner": gym.id,
                "cleaning_weekday": "fri",
                "cleaning_time_window": "afternoon",
                "notes": "Ring doorbell twice",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["gym_partner"], gym.id)
        self.assertEqual(response.data["gym_partner_detail"]["name"], "Partner Gym")
        self.assertEqual(response.data["cleaning_weekday"], "fri")
        self.assertEqual(response.data["notes"], "Ring doorbell twice")

    def test_subscription_preferences_other_user_404(self):
        other = User.objects.create_user(email="other@example.com", password="Pass123!")
        UserProfile.objects.create(user=other, role="tenant")
        UAEIDVerification.objects.create(
            user=self.user, id_hash="abc", status="approved"
        )
        res = Reservation.objects.create(
            listing=self.listing,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="confirmed",
        )
        sub = LifestyleSubscription.objects.create(
            reservation=res,
            plan=self.plan,
            user=self.user,
            start_date="2026-04-01",
            end_date="2027-10-01",
            status="active",
        )
        self.client.force_authenticate(user=other)
        response = self.client.get(
            f"/api/lifestyle-subscriptions/{sub.id}/preferences/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LifestyleInterestFeedbackTests(APITestCase):
    def test_guest_can_submit_interest(self):
        response = self.client.post(
            "/api/lifestyle-interest/",
            {
                "selected": ["cleaning", "utilities"],
                "priority": "utilities",
                "comment": "Need DEWA help on move-in.",
                "email": "guest@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["selected_services"], ["cleaning", "utilities"])
        self.assertEqual(response.data["email"], "guest@example.com")

    def test_authenticated_tenant_uses_account_email(self):
        user = User.objects.create_user(email="tenant@example.com", password="Pass123!")
        UserProfile.objects.create(user=user, role="tenant")
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/api/lifestyle-interest/",
            {"selected": ["gym"], "priority": "gym"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "tenant@example.com")

    def test_other_requires_detail(self):
        response = self.client.post(
            "/api/lifestyle-interest/",
            {"selected": ["other"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
