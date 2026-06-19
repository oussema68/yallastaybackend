from rest_framework import serializers
from .models import Document
from .validators import validate_title_deed_pdf

# Document types only realtors may upload (Dubai brokerage / RERA compliance).
REALTOR_ONLY_DOCUMENT_TYPES = frozenset(
    {
        "realtor_license",
        "trade_license",
        "rera_broker_card",
        "orn",
        "noc_agency",
        "agency_supplementary_licence",
    }
)


class DocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(
        source="get_document_type_display", read_only=True
    )
    content_type_id = serializers.IntegerField(read_only=True)
    related_object = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "document_type",
            "document_type_display",
            "file",
            "content_type_id",
            "object_id",
            "related_object",
            "created_at",
        ]
        read_only_fields = ["user", "created_at"]

    def get_related_object(self, obj):
        if obj.content_type and obj.object_id:
            return (
                f"{obj.content_type.app_label}.{obj.content_type.model}:{obj.object_id}"
            )
        return None


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Accepts content_type_id (ContentType pk) and object_id for linking."""

    content_type_id = serializers.IntegerField(required=False, allow_null=True)
    object_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Document
        fields = ["document_type", "file", "content_type_id", "object_id"]

    def validate_document_type(self, value):
        if value not in [c[0] for c in Document.DOCUMENT_TYPES]:
            raise serializers.ValidationError("Invalid document type.")
        return value

    def validate(self, data):
        ct_id = data.get("content_type_id")
        obj_id = data.get("object_id")
        if (ct_id is None) != (obj_id is None):
            raise serializers.ValidationError(
                "Provide both content_type_id and object_id, or neither."
            )

        doc_type = data.get("document_type")
        request = self.context.get("request")
        if (
            doc_type in REALTOR_ONLY_DOCUMENT_TYPES
            and request
            and request.user.is_authenticated
        ):
            try:
                role = request.user.profile.role
            except Exception:
                role = None
            if role != "realtor":
                raise serializers.ValidationError(
                    {
                        "document_type": "This document type is only for realtor (brokerage) accounts."
                    }
                )

        if doc_type == "title_deed" and request and request.user.is_authenticated:
            try:
                role = request.user.profile.role
            except Exception:
                role = None
            if role != "landlord":
                raise serializers.ValidationError(
                    {
                        "document_type": "Title deed uploads are only for property owner (landlord) accounts."
                    }
                )

        file = data.get("file")
        if doc_type == "title_deed" and file is not None:
            try:
                validate_title_deed_pdf(file)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({"file": exc.detail}) from exc

        return data


class DocumentFileUpdateSerializer(serializers.ModelSerializer):
    """Replace the stored file only (no notification email)."""

    class Meta:
        model = Document
        fields = ["file"]

    def validate_file(self, file):
        if self.instance and self.instance.document_type == "title_deed":
            validate_title_deed_pdf(file)
        return file
