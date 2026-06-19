import re

from rest_framework import serializers
from .models import Listing, ListingImage, Favorite
from core.media_urls import absolute_media_url
from core.serializers import AreaSerializer
from core.text_sanitize import sanitize_plain_text

from django.contrib.auth import get_user_model

from accounts.models import RealtorProfile, UserProfile
from accounts.serializers import VerifiedRealtorSerializer
from documents.models import Document
from documents.access import (
    identity_subject_user_id,
    user_can_view_listing_compliance_files,
)
from documents.validators import ensure_title_deed_document_is_pdf

from .assignment import (
    reset_owner_verification_state,
    validate_property_owner_target,
)
from .emails_assignment import (
    send_broker_assigned_email,
    send_property_owner_linked_email,
)
from .notifications import notify_broker_assigned, notify_property_owner_linked
from notifications.services import notify_user

User = get_user_model()


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ["id", "image", "order"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")
        if ret.get("image") and request:
            ret["image"] = absolute_media_url(request, instance.image)
        return ret


class ListingSerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, read_only=True)
    area_detail = AreaSerializer(source="area", read_only=True)
    listed_by_email = serializers.SerializerMethodField()
    location = serializers.CharField(write_only=True, required=False)
    title_deed_document = serializers.PrimaryKeyRelatedField(
        queryset=Document.objects.none(),
        required=False,
        allow_null=True,
    )
    assigned_realtor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.none(),
        required=False,
        allow_null=True,
    )
    property_owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.none(),
        required=False,
        allow_null=True,
    )
    assigned_realtor_detail = serializers.SerializerMethodField(read_only=True)
    property_owner_detail = serializers.SerializerMethodField(read_only=True)
    title_deed_file_url = serializers.SerializerMethodField()
    owner_uae_id_scan_url = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "description",
            "price",
            "currency",
            "type",
            "leased",
            "status",
            "bedrooms",
            "bathrooms",
            "area_sqft",
            "address",
            "building",
            "location",
            "area",
            "area_detail",
            "trakheesi_permit_number",
            "title_deed_document",
            "title_deed_reference",
            "title_deed_file_url",
            "owner_uae_id_scan_url",
            "assigned_realtor",
            "assigned_realtor_detail",
            "property_owner",
            "property_owner_detail",
            "listed_by",
            "listed_by_email",
            "owner_verification_status",
            "owner_verification_by",
            "owner_verification_note",
            "owner_verification_at",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "listed_by",
            "created_at",
            "updated_at",
            "owner_verification_status",
            "owner_verification_by",
            "owner_verification_note",
            "owner_verification_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["title_deed_document"].queryset = Document.objects.filter(
                user=request.user,
                document_type="title_deed",
            )
        approved_ids = RealtorProfile.objects.filter(is_approved=True).values_list(
            "user_id", flat=True
        )
        self.fields["assigned_realtor"].queryset = User.objects.filter(
            id__in=approved_ids
        )
        landlord_ids = UserProfile.objects.filter(role="landlord").values_list(
            "user_id", flat=True
        )
        self.fields["property_owner"].queryset = User.objects.filter(
            id__in=landlord_ids
        )

    def get_property_owner_detail(self, obj):
        uid = getattr(obj, "property_owner_id", None)
        if not uid:
            return None
        owner = obj.property_owner
        request = self.context.get("request")
        data = {
            "user_id": owner.id,
            "first_name": (owner.first_name or "").strip(),
            "last_name": (owner.last_name or "").strip(),
        }
        if request and request.user.is_authenticated:
            data["email"] = getattr(owner, "email", None)
        return data

    def get_listed_by_email(self, obj):
        """Lister email is sensitive; only expose to authenticated clients (not public scrape)."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        if not obj.listed_by_id:
            return None
        return getattr(obj.listed_by, "email", None)

    def get_assigned_realtor_detail(self, obj):
        uid = getattr(obj, "assigned_realtor_id", None)
        if not uid:
            return None
        try:
            rp = obj.assigned_realtor.realtor_profile
        except RealtorProfile.DoesNotExist:
            return None
        data = VerifiedRealtorSerializer(rp, context=self.context).data
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            data.pop("email", None)
        return data

    def get_title_deed_file_url(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        if not user_can_view_listing_compliance_files(request.user, obj):
            return None
        if not obj.title_deed_document_id:
            return None
        try:
            f = obj.title_deed_document.file
            if f:
                return absolute_media_url(request, f)
        except Exception:
            return None
        return None

    def get_owner_uae_id_scan_url(self, obj):
        """
        Emirates ID scan for the landlord party: verification upload first, else Documents `uae_id`.
        Only for lister, assigned broker, or property owner (compliance / review).
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        if not user_can_view_listing_compliance_files(request.user, obj):
            return None
        uid = identity_subject_user_id(obj)
        if not uid:
            return None
        try:
            owner = User.objects.select_related("uae_id_verification").get(pk=uid)
            v = getattr(owner, "uae_id_verification", None)
            if v and v.document:
                return absolute_media_url(request, v.document.file)
        except Exception:
            pass
        latest = (
            Document.objects.filter(user_id=uid, document_type="uae_id")
            .order_by("-created_at")
            .first()
        )
        if latest and latest.file:
            return absolute_media_url(request, latest.file)
        return None

    def validate(self, data):
        """Dubai DLD: Trakheesi permit; owners must link one title deed per listing."""
        request = self.context.get("request")
        role = None
        if request and request.user.is_authenticated:
            try:
                role = request.user.profile.role
            except Exception:
                role = None

        # assigned_realtor is only for landlords posting their own listing. Realtors use property_owner.
        if role == "realtor" and request and request.user.is_authenticated:
            if self.instance is None:
                if data.get("assigned_realtor") is not None:
                    raise serializers.ValidationError(
                        {
                            "assigned_realtor": (
                                "Only landlords who list their own property can assign a broker here. "
                                "Enter the property owner's landlord user ID instead."
                            )
                        }
                    )
            elif getattr(self.instance, "listed_by_id", None) == request.user.id:
                if (
                    "assigned_realtor" in data
                    and data.get("assigned_realtor") is not None
                ):
                    raise serializers.ValidationError(
                        {
                            "assigned_realtor": (
                                "Only the landlord who lists their own property can assign a broker. "
                                "Send null to clear a mistaken assignment."
                            )
                        }
                    )

        # property_owner: realtor lister links the legal landlord on broker-published listings.
        if "property_owner" in data:
            if role == "landlord":
                if data.get("property_owner") is not None:
                    raise serializers.ValidationError(
                        {
                            "property_owner": (
                                "Landlords who list their own property should assign a verified "
                                "broker instead. Property owner linking is for realtor-published listings."
                            )
                        }
                    )
            elif role != "realtor":
                raise serializers.ValidationError(
                    {
                        "property_owner": (
                            "Only realtor accounts can link a property owner on a listing."
                        )
                    }
                )
            elif (
                self.instance is not None
                and self.instance.listed_by_id != request.user.id
            ):
                raise serializers.ValidationError(
                    {
                        "property_owner": (
                            "Only the realtor who published this listing can link or change the property owner."
                        )
                    }
                )
            else:
                owner_user = data.get("property_owner")
                if owner_user is not None:
                    validate_property_owner_target(owner_user)
                    if owner_user.id == request.user.id:
                        raise serializers.ValidationError(
                            {
                                "property_owner": (
                                    "You cannot set yourself as the property owner on a listing you publish as the broker."
                                )
                            }
                        )

        def _effective_fk(field_name):
            if field_name in data:
                val = data.get(field_name)
                return val.id if val else None
            if self.instance is not None:
                return getattr(self.instance, f"{field_name}_id", None)
            return None

        if _effective_fk("assigned_realtor") and _effective_fk("property_owner"):
            raise serializers.ValidationError(
                "A listing cannot have both an assigned broker and a linked property owner. "
                "Landlords assign a broker on self-listed units; realtors link the owner on broker-listed units."
            )

        for key in ("title", "description", "address", "building", "location"):
            if key in data and data[key] is not None:
                data[key] = sanitize_plain_text(str(data[key]))
        ref = data.get("title_deed_reference")
        if ref is not None:
            data["title_deed_reference"] = sanitize_plain_text(str(ref))[:300]

        if self.instance is None:
            raw = data.get("trakheesi_permit_number")
            num = (str(raw).strip() if raw is not None else "") or ""
            if role == "landlord":
                if num:
                    raise serializers.ValidationError(
                        {
                            "trakheesi_permit_number": "The Trakheesi permit is obtained by your broker through DLD Trakheesi. They will add the 10-digit number after you assign them to this listing."
                        }
                    )
                data["trakheesi_permit_number"] = ""
            else:
                if not re.fullmatch(r"\d{10}", num):
                    raise serializers.ValidationError(
                        {
                            "trakheesi_permit_number": "Enter a valid 10-digit Trakheesi Advertising Permit number. Dubai DLD / RERA require this for every property advertisement you publish as the broker."
                        }
                    )
                data["trakheesi_permit_number"] = num

            if role == "landlord":
                deed = data.get("title_deed_document")
                tref = (data.get("title_deed_reference") or "").strip()
                if not deed:
                    raise serializers.ValidationError(
                        {
                            "title_deed_document": "Property owners must attach one title deed per listing (upload the deed first under documents)."
                        }
                    )
                if not tref:
                    raise serializers.ValidationError(
                        {
                            "title_deed_reference": "Enter the property reference as shown on the title deed (must match the document)."
                        }
                    )
                if deed.user_id != request.user.id:
                    raise serializers.ValidationError(
                        {
                            "title_deed_document": "You can only link your own title deed documents."
                        }
                    )
                if deed.document_type != "title_deed":
                    raise serializers.ValidationError(
                        {"title_deed_document": "Invalid document type."}
                    )

        else:
            if "trakheesi_permit_number" in data:
                raw = data.get("trakheesi_permit_number")
                num = (str(raw).strip() if raw is not None else "") or ""
                if num and not re.fullmatch(r"\d{10}", num):
                    raise serializers.ValidationError(
                        {
                            "trakheesi_permit_number": "Enter a valid 10-digit Trakheesi Advertising Permit number."
                        }
                    )
                inst = self.instance
                uid = getattr(request.user, "id", None) if request else None
                can_set = False
                if uid is not None:
                    if getattr(inst, "listed_by_id", None) == uid:
                        try:
                            if request.user.profile.role == "realtor":
                                can_set = True
                        except Exception:
                            pass
                    if getattr(inst, "assigned_realtor_id", None) == uid:
                        can_set = True
                if not can_set:
                    raise serializers.ValidationError(
                        {
                            "trakheesi_permit_number": "Only the listing broker (assigned realtor or the realtor who published the listing) may set the Trakheesi permit."
                        }
                    )
                data["trakheesi_permit_number"] = num

            if "title_deed_document" in data:
                deed = data.get("title_deed_document")
                if deed is not None:
                    if deed.document_type != "title_deed":
                        raise serializers.ValidationError(
                            {"title_deed_document": "Invalid document type."}
                        )
                    ensure_title_deed_document_is_pdf(deed)

        return data

    def _notify_assignment_changes(
        self, listing, *, old_assigned_id, old_owner_id, actor
    ):
        from messaging.partnership import ensure_partnership_conversation

        assigned_changed = (
            listing.assigned_realtor_id
            and listing.assigned_realtor_id != old_assigned_id
        )
        owner_changed = (
            listing.property_owner_id and listing.property_owner_id != old_owner_id
        )

        intro = None
        if assigned_changed:
            broker_name = (
                getattr(listing.assigned_realtor, "first_name", None) or ""
            ).strip() or "your broker"
            intro = (
                f"I assigned {broker_name} to this listing. "
                "Use this thread to share documents and coordinate Trakheesi and title deed steps."
            )
        elif owner_changed:
            owner_name = (
                getattr(listing.property_owner, "first_name", None) or ""
            ).strip() or "the property owner"
            intro = (
                f"{owner_name} is linked as the property owner. "
                "Share title deed and supporting files here."
            )

        conv = ensure_partnership_conversation(
            listing,
            opened_by=actor,
            intro_text=intro if (assigned_changed or owner_changed) else None,
        )
        messages_link = f"/messages?conversation={conv.id}" if conv else None

        if assigned_changed:
            broker = listing.assigned_realtor
            notify_broker_assigned(broker, listing, landlord=actor, link=messages_link)
            send_broker_assigned_email(broker, listing, landlord=actor)
            if conv and actor != broker:
                notify_user(
                    actor,
                    "listing",
                    "Broker chat opened",
                    f"Messages with your assigned broker for “{listing.title}” are ready.",
                    link=messages_link,
                )
        if owner_changed:
            owner = listing.property_owner
            notify_property_owner_linked(
                owner, listing, realtor=actor, link=messages_link
            )
            send_property_owner_linked_email(owner, listing, realtor=actor)
            if conv and actor != owner:
                notify_user(
                    actor,
                    "listing",
                    "Owner chat opened",
                    f"Messages with the property owner for “{listing.title}” are ready.",
                    link=messages_link,
                )

    def create(self, validated_data):
        from core.models import Area

        request = self.context.get("request")
        location = validated_data.pop("location", None)
        if location:
            area = Area.objects.filter(name__iexact=location).first()
            if area:
                validated_data["area"] = area
            else:
                validated_data["address"] = validated_data.get("address") or location
        listing = super().create(validated_data)
        if request and request.user.is_authenticated:
            self._notify_assignment_changes(
                listing,
                old_assigned_id=None,
                old_owner_id=None,
                actor=request.user,
            )
        return listing

    def update(self, instance, validated_data):
        from core.models import Area

        request = self.context.get("request")
        old_assigned_id = instance.assigned_realtor_id
        old_owner_id = instance.property_owner_id
        location = validated_data.pop("location", None)
        if location:
            area = Area.objects.filter(name__iexact=location).first()
            if area:
                validated_data["area"] = area
            else:
                validated_data["address"] = validated_data.get("address") or location
        if "assigned_realtor" in validated_data:
            new_val = validated_data.get("assigned_realtor")
            new_id = new_val.id if new_val else None
            if new_id != old_assigned_id:
                reset_owner_verification_state(instance.pk)
        listing = super().update(instance, validated_data)
        if request and request.user.is_authenticated:
            self._notify_assignment_changes(
                listing,
                old_assigned_id=old_assigned_id,
                old_owner_id=old_owner_id,
                actor=request.user,
            )
        return listing


class ListingListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list view."""

    area_name = serializers.CharField(source="area.name", read_only=True)
    first_image = serializers.SerializerMethodField()
    assisting_as_realtor = serializers.SerializerMethodField()
    viewer_is_lister = serializers.SerializerMethodField()
    viewer_is_property_owner_only = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "price",
            "currency",
            "type",
            "leased",
            "status",
            "bedrooms",
            "bathrooms",
            "area",
            "area_name",
            "listed_by",
            "assigned_realtor",
            "assisting_as_realtor",
            "viewer_is_lister",
            "viewer_is_property_owner_only",
            "owner_verification_status",
            "first_image",
            "created_at",
        ]

    def get_assisting_as_realtor(self, obj):
        """True when the viewer is the assigned realtor but not the lister (owner-listed unit)."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        try:
            if request.user.profile.role != "realtor":
                return False
        except Exception:
            return False
        return (
            obj.assigned_realtor_id == request.user.id
            and obj.listed_by_id != request.user.id
        )

    def get_viewer_is_lister(self, obj):
        """True when the authenticated user published this listing."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.listed_by_id == request.user.id

    def get_viewer_is_property_owner_only(self, obj):
        """
        True when the viewer is the legal owner on the listing but did not publish it
        (e.g. broker-listed property). Used to split landlord dashboards.
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        po = getattr(obj, "property_owner_id", None)
        if not po:
            return False
        return po == request.user.id and obj.listed_by_id != request.user.id

    def get_first_image(self, obj):
        img = obj.images.first()
        if img and img.image:
            request = self.context.get("request")
            if request:
                return absolute_media_url(request, img.image)
            return img.image.url
        return None


class FavoriteSerializer(serializers.ModelSerializer):
    listing = ListingListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "listing", "created_at"]


class FavoriteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ["listing"]
