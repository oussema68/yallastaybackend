from django.contrib import admin
from .models import Payment, RentSchedule, Deposit


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "amount",
        "currency",
        "payment_type",
        "status",
        "transaction_id",
        "created_at",
    )
    list_filter = ("payment_type", "status")


@admin.register(RentSchedule)
class RentScheduleAdmin(admin.ModelAdmin):
    list_display = ("reservation", "due_date", "amount", "status")


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ("reservation", "amount", "status")
