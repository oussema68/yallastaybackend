from django.db import models
from django.conf import settings
from core.models import Area


class RoommateProfile(models.Model):
    """
    Roommate profile for students/workers looking for shared accommodations.
    Requires UAE ID verification to create/update.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="roommate_profile",
    )
    bio = models.TextField(blank=True)
    budget_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    budget_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    preferred_areas = models.ManyToManyField(
        Area, related_name="roommate_profiles", blank=True
    )
    move_in_date = models.DateField(null=True, blank=True)
    lifestyle_preferences = models.TextField(
        blank=True, help_text="e.g. non-smoker, quiet, pet-friendly"
    )
    is_looking = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Roommate: {self.user.email}"


class RoommateInterest(models.Model):
    """
    User expresses interest in another user as a potential roommate.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="roommate_interests_sent",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="roommate_interests_received",
    )
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [["from_user", "to_user"]]

    def __str__(self):
        return f"{self.from_user.email} → {self.to_user.email} ({self.status})"
