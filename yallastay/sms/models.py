from django.conf import settings
from django.db import models


class SmsTemplate(models.Model):
    """
    Editable SMS bodies. Use `{placeholder}`; callers pass matching keys in ``context``.
    Keep under ~320 chars for single-segment GSM when possible.
    """

    key = models.SlugField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(
        blank=True, help_text="Expected placeholders, e.g. {code}, {property_title}."
    )
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.name} ({self.key})"


class SmsMessage(models.Model):
    """Audit log for outbound SMS (Twilio or compatible)."""

    STATUS_QUEUED = "queued"
    STATUS_SENDING = "sending"
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"
    STATUS_UNDELIVERED = "undelivered"
    STATUS_SKIPPED = "skipped"

    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_SENDING, "Sending"),
        (STATUS_SENT, "Sent"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_FAILED, "Failed"),
        (STATUS_UNDELIVERED, "Undelivered"),
        (STATUS_SKIPPED, "Skipped (no provider)"),
    ]

    to_number = models.CharField(max_length=32, db_index=True)
    body = models.TextField(blank=True)
    template_key = models.CharField(max_length=100, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True, db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True
    )
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sms_messages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.to_number} [{self.status}]"
