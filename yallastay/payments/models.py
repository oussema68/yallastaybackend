from django.db import models
from django.conf import settings
from bookings.models import Reservation


class Payment(models.Model):
    """Payment record (rent, deposit, fee, lifestyle)."""

    TYPE_CHOICES = [
        ("rent", "Rent"),
        ("deposit", "Deposit"),
        ("fee", "Fee"),
        ("lifestyle", "Lifestyle"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
        ("cancelled", "Cancelled"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="AED")
    payment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=255, blank=True)
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    lifestyle_subscription = models.ForeignKey(
        "lifestyle_services.LifestyleSubscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_payments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    team_message_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the Yallastay Team realtor notification was posted to the listing chat.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.amount} {self.currency} ({self.status})"


class RentSchedule(models.Model):
    """Rent due dates linked to a reservation."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
    ]
    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name="rent_schedules"
    )
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="AED")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rent_schedule",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date"]

    def __str__(self):
        return f"Rent {self.due_date} - {self.amount} ({self.status})"


class Deposit(models.Model):
    """Security deposit linked to a reservation."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("held", "Held"),
        ("refunded", "Refunded"),
        ("deducted", "Deducted"),
    ]
    reservation = models.OneToOneField(
        Reservation, on_delete=models.CASCADE, related_name="deposit"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="AED")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deposit_record",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Deposits"

    def __str__(self):
        return f"Deposit {self.reservation_id} - {self.amount} ({self.status})"
