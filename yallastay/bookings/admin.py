from django.contrib import admin
from .models import ViewingRequest, Reservation


@admin.register(ViewingRequest)
class ViewingRequestAdmin(admin.ModelAdmin):
    list_display = ("listing", "user", "requested_datetime", "status")
    list_filter = ("status",)
    search_fields = ("user__email", "listing__title")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "listing",
        "user",
        "start_date",
        "end_date",
        "status",
        "keys_received_at",
        "deposit_amount",
        "external_reference",
    )
    list_filter = ("status",)
    search_fields = ("user__email", "listing__title", "external_reference")
