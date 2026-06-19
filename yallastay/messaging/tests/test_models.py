from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile, LandlordProfile
from core.models import Area
from listings.models import Listing
from messaging.models import Conversation, Message

User = get_user_model()


def _landlord():
    user = User.objects.create_user(email="landlord@example.com", password="Pass123!")
    UserProfile.objects.create(user=user, role="landlord")
    LandlordProfile.objects.create(user=user)
    return user


class ConversationModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )

    def test_create_conversation(self):
        conv = Conversation.objects.create(listing=self.listing)
        conv.participants.add(self.listing.listed_by)
        self.assertEqual(conv.listing, self.listing)


class MessageModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=self.user, role="tenant")
        landlord = _landlord()
        self.listing = Listing.objects.create(
            title="Test",
            description="",
            price=5000,
            type="apartment",
            area=self.area,
            listed_by=landlord,
        )
        self.conv = Conversation.objects.create(listing=self.listing)
        self.conv.participants.add(self.user, landlord)

    def test_create_message(self):
        msg = Message.objects.create(
            conversation=self.conv, sender=self.user, content="Hello!"
        )
        self.assertEqual(msg.content, "Hello!")
        self.assertIsNone(msg.read_at)
