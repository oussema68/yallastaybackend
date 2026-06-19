from django.contrib import admin

from .models import LeaseSigningAuditEvent, LeaseSigningSession


@admin.register(LeaseSigningAuditEvent)
class LeaseSigningAuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "event_type",
        "actor_role",
        "ip_address",
        "created_at",
    )
    list_filter = ("event_type", "actor_role")
    search_fields = ("session__id", "session__renter_token", "session__lister_token")
    raw_id_fields = ("session",)
    readonly_fields = (
        "session",
        "event_type",
        "actor_role",
        "ip_address",
        "user_agent",
        "metadata",
        "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    # Do not override has_delete_permission to False: deleting a LeaseSigningSession
    # CASCADE-deletes audit rows, and the admin checks delete permission on related models.


@admin.register(LeaseSigningSession)
class LeaseSigningSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reservation",
        "status",
        "renter_signed_at",
        "lister_signed_at",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("renter_token", "lister_token", "reservation__listing__title")
    raw_id_fields = ("reservation", "triggering_payment")
    readonly_fields = ("contract_pdf_sha256", "created_at", "updated_at")
