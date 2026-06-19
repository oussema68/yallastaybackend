from django.conf import settings
from django.db import models


class EmailTemplate(models.Model):
    """
    Editable transactional email templates (subject + body).
    Use `{placeholder}` in text; callers pass matching keys in ``context``.
    """

    key = models.SlugField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(
        blank=True,
        help_text="Internal note: which placeholders are expected, e.g. {first_name}, {listing_title}.",
    )
    subject = models.CharField(max_length=255)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.name} ({self.key})"


class EmailMessage(models.Model):
    """Audit log for transactional email (SendGrid, SES, SMTP)."""

    STATUS_QUEUED = "queued"
    STATUS_SENDING = "sending"
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_BOUNCED = "bounced"
    STATUS_FAILED = "failed"
    STATUS_DROPPED = "dropped"
    STATUS_SKIPPED = "skipped"

    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_SENDING, "Sending"),
        (STATUS_SENT, "Sent"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_BOUNCED, "Bounced"),
        (STATUS_FAILED, "Failed"),
        (STATUS_DROPPED, "Dropped"),
        (STATUS_SKIPPED, "Skipped (no backend)"),
    ]

    to_email = models.EmailField(db_index=True)
    subject = models.CharField(max_length=255, blank=True)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
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
        related_name="email_messages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.to_email} [{self.status}]"
