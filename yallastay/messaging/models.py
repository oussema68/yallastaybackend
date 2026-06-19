from django.db import models
from django.conf import settings
from listings.models import Listing


class Conversation(models.Model):
    """Conversation about a listing."""

    KIND_INQUIRY = "inquiry"
    KIND_PARTNERSHIP = "partnership"
    KIND_CHOICES = [
        (KIND_INQUIRY, "Renter inquiry"),
        (KIND_PARTNERSHIP, "Owner and broker"),
    ]

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="conversations"
    )
    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default=KIND_INQUIRY,
        db_index=True,
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="conversations", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "kind"],
                condition=models.Q(kind="partnership"),
                name="messaging_unique_partnership_per_listing",
            )
        ]

    def __str__(self):
        return f"Conversation re {self.listing.title}"


class Message(models.Model):
    """Message in a conversation."""

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    content = models.TextField(blank=True, default="")
    attachment = models.FileField(
        upload_to="messaging/attachments/",
        blank=True,
        null=True,
    )
    attachment_name = models.CharField(max_length=255, blank=True, default="")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.email}: {self.content[:50]}..."
