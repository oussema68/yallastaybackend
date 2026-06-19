from django.db import models
from django.conf import settings
from listings.models import Listing


class Review(models.Model):
    """Rating and review by verified user. Reviewer rates reviewee (e.g. tenant rates landlord)."""

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_given"
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_received",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField()  # 1–5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [["reviewer", "reviewee", "listing"]]

    def __str__(self):
        return f"{self.reviewer.email} → {self.reviewee.email} ({self.rating}★)"


class ReviewResponse(models.Model):
    """Landlord/realtor reply to a review."""

    review = models.OneToOneField(
        Review, on_delete=models.CASCADE, related_name="response"
    )
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Review Response"
        verbose_name_plural = "Review Responses"

    def __str__(self):
        return f"Response to review #{self.review_id}"
