from django.db import models
from django.conf import settings
from listings.models import Listing


class Report(models.Model):
    """Report of a listing or user for moderation."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("reviewed", "Reviewed"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ]
    REPORT_TARGET_CHOICES = [
        ("listing", "Listing"),
        ("user", "User"),
    ]
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_submitted",
    )
    reported_listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, null=True, blank=True, related_name="reports"
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports_against",
    )
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        target = self.reported_listing or self.reported_user
        return f"Report by {self.reporter.email} → {target} ({self.status})"
