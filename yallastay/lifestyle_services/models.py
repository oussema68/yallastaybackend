from django.db import models
from django.conf import settings
from bookings.models import Reservation


class LifestylePlan(models.Model):
    """Essential, Comfort, or Complete tier."""

    name = models.CharField(max_length=100)
    tier = models.PositiveSmallIntegerField(
        unique=True
    )  # 1=Essential, 2=Comfort, 3=Complete
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="AED")
    description = models.TextField(blank=True)
    tagline = models.CharField(
        max_length=200,
        blank=True,
        help_text="Short audience line under the plan name (e.g. Young professionals & single expats).",
    )
    is_most_popular = models.BooleanField(
        default=False,
        help_text="Show “most popular” styling on the lifestyle page.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If false, plan is hidden from the public lifestyle-plans API (existing subscriptions unchanged).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tier"]

    def __str__(self):
        return f"{self.name} (tier {self.tier})"


class LifestylePlanSection(models.Model):
    """Grouped benefits on a plan (e.g. Wellness, Home Services)."""

    plan = models.ForeignKey(
        LifestylePlan, on_delete=models.CASCADE, related_name="sections"
    )
    title = models.CharField(max_length=120)
    emoji = models.CharField(
        max_length=32,
        blank=True,
        help_text="Optional emoji or icon key shown before the section title.",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["plan", "sort_order", "id"]
        verbose_name = "Lifestyle plan section"
        verbose_name_plural = "Lifestyle plan sections"

    def __str__(self):
        return f"{self.plan.name} · {self.title}"


class LifestylePlanBenefit(models.Model):
    """Single bullet line under a section."""

    section = models.ForeignKey(
        LifestylePlanSection, on_delete=models.CASCADE, related_name="benefits"
    )
    text = models.CharField(max_length=500)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["section", "sort_order", "id"]
        verbose_name = "Lifestyle plan benefit"
        verbose_name_plural = "Lifestyle plan benefits"

    def __str__(self):
        return self.text[:60] + ("…" if len(self.text) > 60 else "")


class LifestyleService(models.Model):
    """Legacy: service row keyed by type (pre-section/benefit CMS). Prefer sections in admin."""

    SERVICE_TYPES = [
        ("cleaning", "Cleaning"),
        ("internet", "Internet"),
        ("maintenance", "Maintenance"),
        ("furniture", "Furniture"),
        ("gym", "Gym"),
        ("support", "Support"),
    ]
    plan = models.ForeignKey(
        LifestylePlan, on_delete=models.CASCADE, related_name="services"
    )
    service_type = models.CharField(max_length=30, choices=SERVICE_TYPES)
    details = models.TextField(help_text="e.g. Bi-weekly, Weekly, 2 requests/month")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["plan", "service_type"]
        unique_together = [["plan", "service_type"]]

    def __str__(self):
        return f"{self.plan.name} - {self.get_service_type_display()}"


class LifestyleSubscription(models.Model):
    """User subscription to a plan, linked to a reservation."""

    STATUS_CHOICES = [
        ("pending_payment", "Pending payment"),
        ("active", "Active"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]
    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name="lifestyle_subscriptions"
    )
    plan = models.ForeignKey(
        LifestylePlan, on_delete=models.PROTECT, related_name="subscriptions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lifestyle_subscriptions",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending_payment"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lifestyle Subscription"
        verbose_name_plural = "Lifestyle Subscriptions"

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"


class LifestylePartner(models.Model):
    """Selectable partner (e.g. gym) shown to renters to configure their bundle."""

    PARTNER_TYPES = [
        ("gym", "Gym"),
        ("cleaning_vendor", "Cleaning vendor"),
    ]
    partner_type = models.CharField(max_length=32, choices=PARTNER_TYPES, db_index=True)
    name = models.CharField(max_length=200)
    area_label = models.CharField(
        max_length=120,
        blank=True,
        help_text="Neighborhood or area (e.g. Dubai Marina).",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["partner_type", "sort_order", "id"]
        verbose_name = "Lifestyle partner"
        verbose_name_plural = "Lifestyle partners"

    def __str__(self):
        return f"{self.get_partner_type_display()}: {self.name}"


class LifestyleSubscriptionPreference(models.Model):
    """Renter choices for an active lifestyle subscription (gym, cleaning window, notes)."""

    WEEKDAY_CHOICES = [
        ("mon", "Monday"),
        ("tue", "Tuesday"),
        ("wed", "Wednesday"),
        ("thu", "Thursday"),
        ("fri", "Friday"),
        ("sat", "Saturday"),
        ("sun", "Sunday"),
    ]
    TIME_WINDOW_CHOICES = [
        ("morning", "Morning (8am-12pm)"),
        ("afternoon", "Afternoon (12pm-5pm)"),
        ("evening", "Evening (5pm-9pm)"),
    ]

    subscription = models.OneToOneField(
        LifestyleSubscription,
        on_delete=models.CASCADE,
        related_name="lifestyle_preferences",
    )
    gym_partner = models.ForeignKey(
        LifestylePartner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gym_subscriptions",
        limit_choices_to={"partner_type": "gym", "is_active": True},
    )
    cleaning_weekday = models.CharField(
        max_length=3,
        choices=WEEKDAY_CHOICES,
        default="wed",
    )
    cleaning_time_window = models.CharField(
        max_length=20,
        choices=TIME_WINDOW_CHOICES,
        default="morning",
    )
    notes = models.TextField(
        blank=True,
        help_text="Access instructions, pet notes, or other context for partners.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lifestyle subscription preference"
        verbose_name_plural = "Lifestyle subscription preferences"

    def __str__(self):
        return f"Preferences for subscription {self.subscription_id}"


class LifestyleInterestFeedback(models.Model):
    """Coming-soon lifestyle page: what services renters want before launch."""

    SERVICE_CHOICES = [
        ("cleaning", "Regular home cleaning"),
        ("deep_clean", "Deep clean / move-in cleaning"),
        ("utilities", "Utility setup (DEWA, internet, cooling)"),
        ("gym", "Gym or fitness access"),
        ("laundry", "Laundry & dry cleaning"),
        ("groceries", "Grocery or meal delivery"),
        ("maintenance", "Maintenance & handyman"),
        ("concierge", "Move-in concierge & orientation"),
        ("furniture", "Furniture & home essentials"),
        ("other", "Something else"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lifestyle_interest_feedback",
    )
    email = models.EmailField(blank=True)
    selected_services = models.JSONField(default=list, blank=True)
    priority = models.CharField(max_length=32, blank=True)
    other_detail = models.CharField(max_length=500, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lifestyle interest feedback"
        verbose_name_plural = "Lifestyle interest feedback"

    def __str__(self):
        who = self.email or (self.user.email if self.user_id else "Anonymous")
        return f"Lifestyle interest from {who} ({self.created_at:%Y-%m-%d})"
