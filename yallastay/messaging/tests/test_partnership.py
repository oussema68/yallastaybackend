from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import LandlordProfile, RealtorProfile, UserProfile
from core.models import Area
from documents.models import Document
from listings.models import Listing
from messaging.models import Conversation, Message

User = get_user_model()


def _landlord(email="owner@example.com"):
    user = User.objects.create_user(email=email, password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user, is_approved=True)
    return user


def _realtor(email="broker@example.com"):
    user = User.objects.create_user(email=email, password="Pass123!")
    UserProfile.objects.create(user=user, role="realtor")
    RealtorProfile.objects.create(user=user, agency_name="Agency", is_approved=True)
    return user


class PartnershipConversationTests(APITestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.landlord = _landlord()
        self.realtor = _realtor()

    def test_assigning_realtor_creates_partnership_conversation(self):
        deed = Document.objects.create(
            user=self.landlord,
            document_type="title_deed",
            file=ContentFile(b"%PDF-1.4 test title deed", "title-deed.pdf"),
        )
        self.client.force_authenticate(user=self.landlord)
        response = self.client.post(
            "/api/listings/",
            {
                "title": "Owner unit",
                "description": "Desc",
                "price": 6000,
                "type": "apartment",
                "area": self.area.id,
                "assigned_realtor": self.realtor.id,
                "title_deed_document": deed.id,
                "title_deed_reference": "REF-001",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        listing_id = response.data["id"]
        conv = Conversation.objects.filter(
            listing_id=listing_id, kind=Conversation.KIND_PARTNERSHIP
        ).first()
        self.assertIsNotNone(conv)
        participant_ids = set(conv.participants.values_list("id", flat=True))
        self.assertEqual(participant_ids, {self.landlord.id, self.realtor.id})

    def test_partnership_message_without_uae_id_and_with_attachment(self):
        listing = Listing.objects.create(
            title="Assigned",
            description="Desc",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=self.landlord,
            assigned_realtor=self.realtor,
        )
        from messaging.partnership import ensure_partnership_conversation

        conv = ensure_partnership_conversation(listing, opened_by=self.landlord)
        self.assertIsNotNone(conv)

        self.client.force_authenticate(user=self.landlord)
        from django.core.files.uploadedfile import SimpleUploadedFile

        pdf = SimpleUploadedFile(
            "deed.pdf", b"%PDF-1.4 test", content_type="application/pdf"
        )
        response = self.client.post(
            f"/api/conversations/{conv.id}/messages/",
            {"content": "Title deed attached", "attachment": pdf},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["has_attachment"])
        self.assertEqual(response.data["attachment_name"], "deed.pdf")
        self.assertTrue(
            Message.objects.filter(conversation=conv, attachment__isnull=False).exists()
        )

    def test_realtor_listed_owner_link_creates_partnership_chat(self):
        owner = _landlord("owner2@example.com")
        listing = Listing.objects.create(
            title="Broker listed",
            description="Desc",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=self.realtor,
            trakheesi_permit_number="1234567890",
        )
        self.client.force_authenticate(user=self.realtor)
        response = self.client.patch(
            f"/api/listings/{listing.id}/",
            {"property_owner": owner.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        conv = Conversation.objects.filter(
            listing=listing, kind=Conversation.KIND_PARTNERSHIP
        ).first()
        self.assertIsNotNone(conv)
        self.assertIn(owner.id, conv.participants.values_list("id", flat=True))
