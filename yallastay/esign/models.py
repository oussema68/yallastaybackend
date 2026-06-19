from django.db import models

from bookings.models import Reservation


class LeaseSigningSession(models.Model):
    """
    Stub e-sign flow: magic-link tokens per party. Replace with DocuSign/Dropbox Sign
    webhooks + external id in ``provider_metadata`` when integrating a vendor.
    """

    STATUS_CHOICES = [
        ("pending", "Pending signatures"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name="lease_signing",
    )
    triggering_payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_signing_sessions",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    renter_token = models.CharField(max_length=64, unique=True, db_index=True)
    lister_token = models.CharField(max_length=64, unique=True, db_index=True)
    renter_signed_at = models.DateTimeField(null=True, blank=True)
    lister_signed_at = models.DateTimeField(null=True, blank=True)
    provider_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Future: DocuSign envelope id, Dropbox Sign signature_request_id, etc.",
    )
    signature_field_boxes = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Optional. Renter/lister signature rectangles on the contract PDF (points, PDF bottom-left origin): "
            '{"renter": {"page_index": 0, "x": 72, "y": 72, "width": 200, "height": 48}, "lister": {...}}. '
            "When set (both parties), signed PDFs overlay images on these boxes instead of appending certificate pages."
        ),
    )
    lister_contract_pdf = models.FileField(
        upload_to="esign/lister_uploads/%Y/%m/",
        blank=True,
        max_length=500,
        help_text="Tenancy contract uploaded by the listing owner / realtor; shown to both parties for signing.",
    )
    contract_pdf = models.FileField(
        upload_to="esign/contracts/%Y/%m/",
        blank=True,
        max_length=500,
        help_text="Auto-generated fallback PDF (dev) when no lister upload; superseded by lister_contract_pdf.",
    )
    contract_pdf_sha256 = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 hex of contract_pdf at generation (integrity reference).",
    )
    signed_pdf = models.FileField(
        upload_to="esign/signed/%Y/%m/",
        blank=True,
        null=True,
        max_length=500,
        help_text="Signed contract: either overlays on signature_field_boxes or contract + certificate pages.",
    )
    renter_signature_image = models.FileField(
        upload_to="esign/signatures/%Y/%m/",
        blank=True,
        max_length=500,
        help_text="PNG captured when the renter signs (embedded on certificate page).",
    )
    lister_signature_image = models.FileField(
        upload_to="esign/signatures/%Y/%m/",
        blank=True,
        max_length=500,
        help_text="PNG captured when the landlord/realtor signs (embedded on certificate page).",
    )
    renter_signature_slot_1 = models.FileField(
        upload_to="esign/signatures/%Y/%m/",
        blank=True,
        max_length=500,
        help_text="Renter PNG for placement 1 when contract uses three signature areas.",
    )
    renter_signature_slot_2 = models.FileField(
        upload_to="esign/signatures/%Y/%m/",
        blank=True,
        max_length=500,
        help_text="Renter PNG for placement 2.",
    )
    renter_signature_slot_3 = models.FileField(
        upload_to="esign/signatures/%Y/%m/",
        blank=True,
        max_length=500,
        help_text="Renter PNG for placement 3.",
    )
    lister_signature_slot_1 = models.FileField(
        upload_to="esign/signatures/%Y/%m/",
        blank=True,
        max_length=500,
        help_text="Lister PNG for placement 1 when contract uses three signature areas.",
    )
    lister_signature_slot_2 = models.FileField(
        upload_to="esign/signatures/%Y/%m/",
        blank=True,
        max_length=500,
        help_text="Lister PNG for placement 2.",
    )
    lister_signature_slot_3 = models.FileField(
        upload_to="esign/signatures/%Y/%m/",
        blank=True,
        max_length=500,
        help_text="Lister PNG for placement 3.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"LeaseSigning #{self.pk} reservation={self.reservation_id} ({self.status})"
        )


class LeaseSigningAuditEvent(models.Model):
    """
    Immutable audit trail for magic-link signing (UAE Federal Decree-Law No. 46 of 2021  -
    identifiable electronic records). Not a substitute for a qualified trust-service signature.
    """

    class EventType(models.TextChoices):
        SIGN_PREVIEW_ACCESSED = "sign_preview_accessed", "Sign preview accessed"
        CONTRACT_PDF_VIEWED = "contract_pdf_viewed", "Contract PDF viewed"
        ELECTRONIC_CONSENT_ACCEPTED = (
            "electronic_consent_accepted",
            "Electronic consent accepted",
        )
        SIGNATURE_COMMITTED = "signature_committed", "Signature committed"
        SIGNING_SESSION_COMPLETED = (
            "signing_session_completed",
            "Signing session completed",
        )

    session = models.ForeignKey(
        LeaseSigningSession,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    event_type = models.CharField(max_length=64, choices=EventType.choices)
    actor_role = models.CharField(max_length=20, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session", "-created_at"]),
        ]

    def __str__(self):
        return f"Audit {self.event_type} session={self.session_id} @ {self.created_at}"
