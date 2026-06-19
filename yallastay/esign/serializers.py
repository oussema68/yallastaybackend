from rest_framework import serializers

from .models import LeaseSigningSession
from .parties import lease_signing_lister_user
from .services import session_has_contract_pdf
from .signing_slots import renter_placements_missing_for_lister_upload


class LeaseSigningSessionSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(
        source="reservation.listing.title", read_only=True
    )
    listing_id = serializers.IntegerField(
        source="reservation.listing_id", read_only=True
    )
    reservation_id = serializers.IntegerField(read_only=True)
    my_sign_url = serializers.SerializerMethodField()
    viewer_role = serializers.SerializerMethodField()
    can_sign = serializers.SerializerMethodField()
    instructions = serializers.SerializerMethodField()
    signing_progress = serializers.SerializerMethodField()
    pdf_api_url = serializers.SerializerMethodField()
    contract_pdf_ready = serializers.SerializerMethodField()
    needs_lister_contract_upload = serializers.SerializerMethodField()
    can_upload_contract = serializers.SerializerMethodField()
    listing_has_property_owner = serializers.SerializerMethodField()

    class Meta:
        model = LeaseSigningSession
        fields = (
            "id",
            "reservation_id",
            "listing_id",
            "listing_title",
            "status",
            "renter_signed_at",
            "lister_signed_at",
            "created_at",
            "my_sign_url",
            "pdf_api_url",
            "contract_pdf_ready",
            "needs_lister_contract_upload",
            "can_upload_contract",
            "signature_field_boxes",
            "viewer_role",
            "listing_has_property_owner",
            "can_sign",
            "instructions",
            "signing_progress",
        )
        read_only_fields = fields

    def get_viewer_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        reservation = obj.reservation
        listing = reservation.listing
        uid = request.user.id
        if uid == reservation.user_id:
            return "renter"
        signer = lease_signing_lister_user(listing)
        if uid == signer.id:
            try:
                role = request.user.profile.role
            except Exception:
                role = None
            if role == "realtor":
                return "realtor_lister"
            return "landlord_lister"
        if uid == listing.listed_by_id:
            return "listing_agent"
        return None

    def get_listing_has_property_owner(self, obj):
        return bool(obj.reservation.listing.property_owner_id)

    def get_contract_pdf_ready(self, obj):
        return session_has_contract_pdf(obj)

    def get_needs_lister_contract_upload(self, obj):
        vr = self.get_viewer_role(obj)
        if vr not in ("landlord_lister", "realtor_lister", "listing_agent"):
            return False
        return (
            obj.status == "pending"
            and not obj.renter_signed_at
            and not session_has_contract_pdf(obj)
        )

    def get_can_upload_contract(self, obj):
        vr = self.get_viewer_role(obj)
        if vr not in ("landlord_lister", "realtor_lister", "listing_agent"):
            return False
        return obj.status == "pending" and not obj.renter_signed_at

    def get_can_sign(self, obj):
        vr = self.get_viewer_role(obj)
        if not session_has_contract_pdf(obj):
            return False
        if vr == "renter":
            if renter_placements_missing_for_lister_upload(obj):
                return False
            return obj.status == "pending" and not obj.renter_signed_at
        if vr in ("landlord_lister", "realtor_lister"):
            if obj.status != "pending" or obj.lister_signed_at:
                return False
            return bool(obj.renter_signed_at)
        return False

    def get_instructions(self, obj):
        vr = self.get_viewer_role(obj)
        has_pdf = session_has_contract_pdf(obj)
        if vr == "renter":
            if obj.status == "completed":
                return "Lease fully signed."
            if obj.renter_signed_at:
                return "You’ve signed. Waiting for the landlord to countersign."
            if not has_pdf:
                return "Waiting for the lease PDF to be uploaded. You’ll be able to sign once it appears here."
            return "Sign the tenancy agreement (Step 1 of 2). The landlord signs after you."
        if vr == "landlord_lister":
            if obj.status == "completed":
                return "Lease fully signed."
            if not has_pdf:
                return "Upload the tenancy agreement PDF below (PDF only). The renter can sign after it’s available."
            if not obj.renter_signed_at:
                return "Wait for the renter to sign first. You’ll get an email when you can countersign (Step 2 of 2)."
            if not obj.lister_signed_at:
                return "The renter has signed. Review and sign to complete the lease (Step 2 of 2)."
            return ""
        if vr == "realtor_lister":
            if obj.status == "completed":
                return "Lease fully signed."
            if not has_pdf:
                return (
                    "Upload the tenancy agreement PDF below (PDF only). The renter can sign after it’s available. "
                    "Best practice: invite the property owner to register, set them as owner on the listing, "
                    "so they countersign - not you as the realtor."
                )
            if not obj.renter_signed_at:
                return (
                    "Wait for the renter to sign first. Prefer the landlord to countersign: invite them below, "
                    "set them as property owner on the listing, then they receive the signing link."
                )
            if not obj.lister_signed_at:
                return (
                    "The renter has signed. If the landlord is on the platform, add them as property owner on the listing "
                    "and ask them to sign - or sign here only if you are authorized to bind the landlord side."
                )
            return ""
        if vr == "listing_agent":
            if obj.status == "completed":
                return "Lease fully signed."
            if not has_pdf:
                return "Upload the tenancy agreement PDF below if you are preparing the file on behalf of the owner. The property owner signs the lease (not the realtor)."
            if not obj.renter_signed_at:
                return "Wait for the renter to sign first. The property owner will countersign after you place signature fields."
            if not obj.lister_signed_at:
                return "The renter has signed. The property owner must complete the landlord signature step."
            return ""
        return ""

    def get_signing_progress(self, obj):
        """Short label for dashboard chips."""
        if obj.status == "completed":
            return "complete"
        if not obj.renter_signed_at:
            return "waiting_renter"
        if not obj.lister_signed_at:
            return "waiting_lister"
        return "pending"

    def get_my_sign_url(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        user = request.user
        reservation = obj.reservation
        listing = reservation.listing
        signer = lease_signing_lister_user(listing)
        from .frontend_urls import frontend_base_url

        base = frontend_base_url()
        if user.id == reservation.user_id and not obj.renter_signed_at:
            return f"{base}/sign/lease/{obj.renter_token}"
        if user.id == signer.id and not obj.lister_signed_at:
            if not obj.renter_signed_at:
                return None
            return f"{base}/sign/lease/{obj.lister_token}"
        return None

    def get_pdf_api_url(self, obj):
        """Relative path for `publicApiUrl()` - same-origin PDF for iframe."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        user = request.user
        reservation = obj.reservation
        listing = reservation.listing
        signer = lease_signing_lister_user(listing)
        if user.id == reservation.user_id:
            t = obj.renter_token
            return f"/esign/sign/{t}/pdf/"
        if user.id == signer.id:
            t = obj.lister_token
            return f"/esign/sign/{t}/pdf/"
        if user.id == listing.listed_by_id and signer.id != user.id:
            # Realtor: do not expose lister token in the dashboard; use JWT session PDF.
            return f"/esign/sessions/{obj.pk}/contract-pdf/"
        return None
