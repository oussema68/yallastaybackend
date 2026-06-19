from django.db import models
from django.conf import settings
from listings.models import Listing


class ViewingRequest(models.Model):
    """Viewing request by student/worker. Requires UAE ID verification."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("rejected", "Rejected"),
    ]
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="viewing_requests"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="viewing_requests",
    )
    requested_datetime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Viewing Request"
        verbose_name_plural = "Viewing Requests"

    def __str__(self):
        return f"{self.user.email} - {self.listing.title} ({self.status})"


class Reservation(models.Model):
    """In-app rental request (tenant → lister). UAE ID required to create. DLD sync later."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="reservations"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="AED")
    notes = models.TextField(
        blank=True,
        help_text="Optional message from the renter to the lister.",
    )
    # Placeholders for future Dubai DLD / contract registry integration
    external_reference = models.CharField(
        max_length=120,
        blank=True,
        help_text="External contract or DLD reference when synced.",
    )
    dld_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Opaque payload for future DLD/DRD API sync (status, ids, etc.).",
    )
    keys_received_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the renter confirmed they collected keys (in-app handover checkpoint).",
    )
    platform_feedback = models.TextField(
        blank=True,
        help_text="Optional private feedback from the renter about the platform (not a public review).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.listing.title} ({self.start_date} to {self.end_date})"
