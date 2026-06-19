from django.db import models
from django.conf import settings


class Notification(models.Model):
    """In-app notification for a user."""

    TYPE_CHOICES = [
        ("booking", "Booking"),
        ("viewing", "Viewing"),
        ("message", "Message"),
        ("payment", "Payment"),
        ("lifestyle", "Lifestyle"),
        ("review", "Review"),
        ("listing", "Listing"),
        ("general", "General"),
        ("welcome", "Welcome"),
        ("email_verified", "Email verified"),
        ("documents_verified", "Documents verified"),
        ("uae_verified", "UAE ID verified"),
        ("acceptance", "Acceptance"),
        ("contract", "Contract"),
        ("esign", "E-sign / lease"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    link = models.CharField(
        max_length=500,
        blank=True,
        help_text="Frontend path (e.g. /dashboard) or absolute URL.",
    )
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class NotificationPreference(models.Model):
    """User preference for notification channels and types."""

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("push", "Push"),
        ("in_app", "In-App"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    notification_type = models.CharField(max_length=30, default="general")
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["user", "channel", "notification_type"]]
        ordering = ["user", "channel"]

    def __str__(self):
        return f"{self.user.email} - {self.channel}:{self.notification_type}"
