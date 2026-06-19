from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile, LandlordProfile, UAEIDVerification
from core.models import Area
from listings.models import Listing
from messaging.models import Conversation, Message

User = get_user_model()


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


class MessagingViewTests(APITestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.user1 = User.objects.create_user(
            email="user1@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user1, role="tenant")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="Desc",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )

    def test_list_conversations_requires_auth(self):
        response = self.client.get("/api/conversations/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_conversations_authenticated(self):
        self.client.force_authenticate(user=self.user1)
        with self.assertLogs("messaging.views", level="INFO") as cm:
            response = self.client.get("/api/conversations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any("messaging.conversation.list" in r.getMessage() for r in cm.records)
        )

    def test_create_conversation_requires_uae_id(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            "/api/conversations/", {"listing_id": self.listing.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_conversation_with_uae_id(self):
        UAEIDVerification.objects.create(
            user=self.user1, id_hash="abc", status="approved"
        )
        self.client.force_authenticate(user=self.user1)
        with self.assertLogs("messaging.views", level="INFO") as cm:
            response = self.client.post(
                "/api/conversations/", {"listing_id": self.listing.id}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Conversation.objects.filter(listing=self.listing).exists())
        self.assertTrue(
            any("messaging.conversation.create" in r.getMessage() for r in cm.records)
        )

    def test_send_message(self):
        UAEIDVerification.objects.create(
            user=self.user1, id_hash="abc", status="approved"
        )
        conv = Conversation.objects.create(
            listing=self.listing, kind=Conversation.KIND_INQUIRY
        )
        conv.participants.add(self.user1, self.listing.listed_by)
        self.client.force_authenticate(user=self.user1)
        with self.assertLogs("messaging.views", level="INFO") as cm:
            response = self.client.post(
                f"/api/conversations/{conv.id}/messages/",
                {
                    "content": "Hello, is this available?",
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Message.objects.filter(conversation=conv, sender=self.user1).exists()
        )
        self.assertTrue(
            any("messaging.message.create" in r.getMessage() for r in cm.records)
        )

    def test_conversation_detail(self):
        conv = Conversation.objects.create(listing=self.listing)
        conv.participants.add(self.user1, self.listing.listed_by)
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"/api/conversations/{conv.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_messages(self):
        conv = Conversation.objects.create(listing=self.listing)
        conv.participants.add(self.user1, self.listing.listed_by)
        Message.objects.create(conversation=conv, sender=self.user1, content="Hi")
        self.client.force_authenticate(user=self.user1)
        with self.assertLogs("messaging.views", level="INFO") as cm:
            response = self.client.get(f"/api/conversations/{conv.id}/messages/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any("messaging.messages.list" in r.getMessage() for r in cm.records)
        )
        self.assertIn("messages", response.data)
        self.assertIn("conversation", response.data)
        msgs = response.data["messages"]
        self.assertEqual(len(msgs), 1)
        row = msgs[0]
        self.assertEqual(row["sender"], self.user1.id)
        self.assertIn("sender_first_name", row)
        self.assertIn("sender_is_yallastay_team", row)
        self.assertFalse(row["sender_is_yallastay_team"])
        conv_payload = response.data["conversation"]
        self.assertEqual(conv_payload["listing"], self.listing.id)
        self.assertEqual(conv_payload["listing_detail"]["title"], "Test")
        self.assertEqual(conv_payload["other_user"]["id"], self.listing.listed_by_id)

    def test_message_mark_read(self):
        conv = Conversation.objects.create(listing=self.listing)
        conv.participants.add(self.user1, self.listing.listed_by)
        msg = Message.objects.create(
            conversation=conv, sender=self.listing.listed_by, content="Hi"
        )
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            f"/api/conversations/{conv.id}/messages/{msg.id}/read/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_conversation_mark_all_read(self):
        conv = Conversation.objects.create(listing=self.listing)
        conv.participants.add(self.user1, self.listing.listed_by)
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(f"/api/conversations/{conv.id}/mark-read/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
