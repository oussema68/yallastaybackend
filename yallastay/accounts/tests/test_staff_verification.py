from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import LandlordProfile, RealtorProfile, UserProfile
from documents.models import Document
from notifications.models import Notification

User = get_user_model()


class StaffVerificationAPITests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            email="verify@team.example.com", password="Pass123!"
        )
        UserProfile.objects.create(
            user=self.staff_user,
            role="tenant",
            can_verify_documents=True,
        )
        self.realtor = User.objects.create_user(
            email="broker@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.realtor, role="realtor")
        RealtorProfile.objects.create(
            user=self.realtor,
            agency_name="Test Agency",
            brokerage_type="private",
        )
        self.landlord = User.objects.create_user(
            email="owner@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.landlord, role="landlord")
        LandlordProfile.objects.create(user=self.landlord, is_emirati=False)

    def test_queue_requires_verification_staff(self):
        outsider = User.objects.create_user(
            email="outsider@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=outsider, role="tenant")
        self.client.force_authenticate(user=outsider)
        r = self.client.get("/api/staff/verification/queue/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_queue_lists_pending_broker_and_owner(self):
        self.client.force_authenticate(user=self.staff_user)
        r = self.client.get("/api/staff/verification/queue/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = [row["user_id"] for row in r.data["realtors"]]
        self.assertIn(self.realtor.id, ids)
        lids = [row["user_id"] for row in r.data["landlords"]]
        self.assertIn(self.landlord.id, lids)

    def test_approve_realtor(self):
        self.client.force_authenticate(user=self.staff_user)
        r = self.client.post(
            f"/api/staff/verification/realtors/{self.realtor.id}/decision/",
            {"action": "approve"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.realtor.realtor_profile.refresh_from_db()
        self.assertTrue(self.realtor.realtor_profile.is_approved)

    def test_reject_realtor_sends_notification(self):
        self.client.force_authenticate(user=self.staff_user)
        before = Notification.objects.filter(user=self.realtor).count()
        r = self.client.post(
            f"/api/staff/verification/realtors/{self.realtor.id}/decision/",
            {"action": "reject", "message": "Please upload a clearer trade licence."},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Notification.objects.filter(user=self.realtor).count(), before + 1
        )

    def test_approve_landlord(self):
        self.client.force_authenticate(user=self.staff_user)
        r = self.client.post(
            f"/api/staff/verification/landlords/{self.landlord.id}/decision/",
            {"action": "approve"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.landlord.landlord_profile.refresh_from_db()
        self.assertTrue(self.landlord.landlord_profile.is_approved)

    def test_django_is_staff_also_allowed(self):
        admin_u = User.objects.create_user(
            email="djstaff@example.com", password="Pass123!", is_staff=True
        )
        UserProfile.objects.create(user=admin_u, role="tenant")
        self.client.force_authenticate(user=admin_u)
        r = self.client.get("/api/staff/verification/queue/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)


class StaffDocumentAccessTests(APITestCase):
    def test_verification_staff_can_get_other_user_document(self):
        owner = User.objects.create_user(
            email="docowner@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=owner, role="realtor")
        RealtorProfile.objects.create(
            user=owner, agency_name="X", brokerage_type="private"
        )
        doc = Document.objects.create(
            user=owner,
            document_type="trade_license",
            file=SimpleUploadedFile(
                "t.pdf", b"%PDF-1.4", content_type="application/pdf"
            ),
        )
        staff = User.objects.create_user(
            email="docstaff@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=staff, role="tenant", can_verify_documents=True)
        self.client.force_authenticate(user=staff)
        r = self.client.get(f"/api/documents/{doc.id}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["document_type"], "trade_license")
