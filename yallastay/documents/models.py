from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Document(models.Model):
    """
    Centralized document storage. Can be linked to UAEIDVerification,
    LeaseAgreement, UniversityVerification, RealtorProfile, etc.
    """

    DOCUMENT_TYPES = [
        ("uae_id", "UAE ID (supporting scan / copy)"),
        ("university", "University Verification"),
        ("lease_agreement", "Lease Agreement"),
        ("realtor_license", "Realtor / brokerage license"),
        ("trade_license", "Trade licence (DET / Free Zone)"),
        ("rera_broker_card", "RERA Broker Card (BRN)"),
        ("orn", "ORN (Office Registration Number) certificate"),
        ("agency_supplementary_licence", "Agency / supplementary licence"),
        ("noc_agency", "NOC (sponsoring agency)"),
        ("passport", "Passport"),
        ("residence_visa", "Residence visa"),
        ("title_deed", "Title deed (property ownership, PDF only)"),
        ("other", "Other"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to="documents/%Y/%m/")
    # Optional: link to a related object (e.g. UAEIDVerification, LeaseAgreement)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.get_document_type_display()} ({self.created_at.date()})"
