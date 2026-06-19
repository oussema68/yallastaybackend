from urllib.parse import unquote

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from .password_reset import password_reset_token_generator
from core.models import Area, University
from core.text_sanitize import sanitize_plain_text

from .models import LandlordProfile, RealtorProfile, UserProfile

User = get_user_model()


class AreaMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ["id", "name", "slug"]


class UserProfileSerializer(serializers.ModelSerializer):
    work_area = AreaMinimalSerializer(read_only=True)
    work_area_id = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(),
        source="work_area",
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = UserProfile
        fields = [
            "role",
            "phone",
            "work_area",
            "work_area_id",
            "bio",
            "place_of_work_or_studies",
            "sex",
            "age",
            "is_email_verified",
            "email_verified_at",
            "can_manage_lifestyle",
            "can_verify_documents",
        ]
        read_only_fields = [
            "is_email_verified",
            "email_verified_at",
            "can_manage_lifestyle",
            "can_verify_documents",
        ]


class UserProfileUpdateSerializer(serializers.Serializer):
    """Update user + profile (first_name, last_name, phone, work_area_id, bio, renter extras)."""

    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    work_area_id = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), required=False, allow_null=True
    )
    bio = serializers.CharField(required=False, allow_blank=True)
    place_of_work_or_studies = serializers.CharField(
        max_length=300, required=False, allow_blank=True
    )
    sex = serializers.ChoiceField(
        choices=UserProfile.SEX_CHOICES,
        required=False,
        allow_blank=True,
    )
    age = serializers.IntegerField(
        required=False, allow_null=True, min_value=13, max_value=120
    )
    orn = serializers.CharField(max_length=64, required=False, allow_blank=True)
    rera_number = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    is_emirati = serializers.BooleanField(required=False, allow_null=True)
    brokerage_type = serializers.ChoiceField(
        choices=RealtorProfile.BROKERAGE_TYPE_CHOICES,
        required=False,
    )

    def validate_first_name(self, value):
        if value is None or value == "":
            return value
        v = sanitize_plain_text(value).strip()
        return v or value

    def validate_last_name(self, value):
        if value is None or value == "":
            return value
        v = sanitize_plain_text(value).strip()
        return v or value

    def validate_bio(self, value):
        return sanitize_plain_text(value or "")

    def validate_place_of_work_or_studies(self, value):
        return sanitize_plain_text(value or "")

    def validate_phone(self, value):
        return sanitize_plain_text(value or "")

    def validate_orn(self, value):
        return sanitize_plain_text(value or "")

    def validate_rera_number(self, value):
        return sanitize_plain_text(value or "")

    def update(self, instance, validated_data):

        user = instance
        if "first_name" in validated_data:
            user.first_name = validated_data["first_name"]
        if "last_name" in validated_data:
            user.last_name = validated_data["last_name"]
        user.save()

        try:
            profile = user.profile
        except Exception:
            profile = None

        if profile:
            dirty = False
            if "phone" in validated_data:
                profile.phone = validated_data["phone"]
                dirty = True
            if "work_area_id" in validated_data:
                profile.work_area = validated_data["work_area_id"]
                dirty = True
            if "bio" in validated_data:
                profile.bio = validated_data["bio"]
                dirty = True
            if profile.role in ("tenant", "student"):
                if "place_of_work_or_studies" in validated_data:
                    profile.place_of_work_or_studies = (
                        validated_data["place_of_work_or_studies"] or ""
                    ).strip()
                    dirty = True
                if "sex" in validated_data:
                    profile.sex = validated_data["sex"] or ""
                    dirty = True
                if "age" in validated_data:
                    profile.age = validated_data["age"]
                    dirty = True
            if dirty:
                profile.save()

        if profile and profile.role == "landlord":
            if "is_emirati" in validated_data:
                lp, _ = LandlordProfile.objects.get_or_create(user=user)
                lp.is_emirati = validated_data["is_emirati"]
                lp.save(update_fields=["is_emirati", "updated_at"])

        if profile and profile.role == "realtor":
            try:
                rp = user.realtor_profile
            except Exception:
                rp = None
            if rp:
                dirty_rp = False
                if "orn" in validated_data:
                    rp.orn = validated_data["orn"] or ""
                    dirty_rp = True
                if "rera_number" in validated_data:
                    rp.rera_number = validated_data["rera_number"] or ""
                    dirty_rp = True
                if "brokerage_type" in validated_data:
                    rp.brokerage_type = validated_data["brokerage_type"]
                    dirty_rp = True
                if dirty_rp:
                    rp.save()

        return user


class VerifiedRealtorSerializer(serializers.ModelSerializer):
    """Public-safe fields for owners choosing a verified realtor."""

    user_id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = RealtorProfile
        fields = [
            "user_id",
            "email",
            "agency_name",
            "brokerage_type",
            "rera_number",
            "orn",
            "is_approved",
        ]


class RealtorProfileMinimalSerializer(serializers.ModelSerializer):
    """Exposed on /auth/me/ so the client can gate listing without extra calls."""

    license_document_uploaded = serializers.SerializerMethodField()

    class Meta:
        model = RealtorProfile
        fields = [
            "is_approved",
            "license_document_uploaded",
            "approved_at",
            "orn",
            "rera_number",
            "agency_name",
            "brokerage_type",
        ]

    def get_license_document_uploaded(self, obj):
        return bool(obj.license_document)


class LandlordProfileMinimalSerializer(serializers.ModelSerializer):
    """Exposed on /auth/me/ so the client can show owner verification like realtors."""

    class Meta:
        model = LandlordProfile
        fields = ["is_approved", "approved_at"]


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    realtor_profile = serializers.SerializerMethodField()
    landlord_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_superuser",
            "profile",
            "role",
            "realtor_profile",
            "landlord_profile",
        ]
        read_only_fields = ["email", "is_staff", "is_superuser"]

    def get_profile(self, obj):
        try:
            return UserProfileSerializer(obj.profile).data
        except Exception:
            return None

    def get_role(self, obj):
        try:
            return obj.profile.role
        except Exception:
            return None

    def get_realtor_profile(self, obj):
        try:
            if obj.profile.role != "realtor":
                return None
            return RealtorProfileMinimalSerializer(obj.realtor_profile).data
        except Exception:
            return None

    def get_landlord_profile(self, obj):
        try:
            if obj.profile.role != "landlord":
                return None
            return LandlordProfileMinimalSerializer(obj.landlord_profile).data
        except Exception:
            return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=[
            ("tenant", "tenant"),
            ("landlord", "landlord"),
            ("realtor", "realtor"),
        ],
        default="tenant",
    )
    phone = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)
    needs_assisted_listing = serializers.BooleanField(default=False, required=False)
    agency_name = serializers.CharField(required=False, allow_blank=True)
    listing_owner_invite_token = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "phone",
            "name",
            "needs_assisted_listing",
            "agency_name",
            "listing_owner_invite_token",
        ]

    def validate_first_name(self, value):
        if value is None or value == "":
            return value
        return sanitize_plain_text(value).strip()

    def validate_last_name(self, value):
        if value is None or value == "":
            return value
        return sanitize_plain_text(value).strip()

    def validate_phone(self, value):
        return sanitize_plain_text(value or "")

    def validate_name(self, value):
        return sanitize_plain_text(value or "")

    def validate_agency_name(self, value):
        return sanitize_plain_text(value or "")

    def create(self, validated_data):
        from .models import UserProfile, LandlordProfile, RealtorProfile

        role = validated_data.pop("role", "tenant")
        phone = validated_data.pop("phone", "")
        name = validated_data.pop("name", "")
        needs_assisted_listing = validated_data.pop("needs_assisted_listing", False)
        agency_name = validated_data.pop("agency_name", "")
        invite_token = (
            validated_data.pop("listing_owner_invite_token", "") or ""
        ).strip()

        if name:
            parts = name.split(maxsplit=1)
            validated_data["first_name"] = validated_data.get("first_name") or parts[0]
            validated_data["last_name"] = validated_data.get("last_name") or (
                parts[1] if len(parts) > 1 else ""
            )

        user = User.objects.create_user(**validated_data)

        UserProfile.objects.create(user=user, role=role, phone=phone)

        if role == "landlord":
            LandlordProfile.objects.create(
                user=user, needs_assisted_listing=needs_assisted_listing
            )
        elif role == "realtor":
            RealtorProfile.objects.create(
                user=user, agency_name=agency_name or user.email
            )

        if invite_token and role == "landlord":
            try:
                from listings.owner_invites import (
                    OwnerInviteError,
                    accept_listing_owner_invite,
                )

                accept_listing_owner_invite(token=invite_token, user=user)
            except OwnerInviteError:
                pass

        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        uid = unquote((attrs.get("uid") or "").strip())
        token = unquote((attrs.get("token") or "").strip())
        try:
            pk = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise serializers.ValidationError("Invalid or expired password reset link.")
        if not password_reset_token_generator.check_token(user, token):
            raise serializers.ValidationError("Invalid or expired password reset link.")
        validate_password(attrs["new_password"], user)
        attrs["_user"] = user
        return attrs


# --- Verification serializers ---


class UAEIDVerificationSerializer(serializers.Serializer):
    """Submit UAE ID for verification. ID is hashed before storage."""

    emirates_id = serializers.CharField(max_length=50, required=True)
    document = serializers.FileField(required=False, allow_null=True)

    def validate_emirates_id(self, value):
        if not value or len(value) < 10:
            raise serializers.ValidationError("Invalid Emirates ID format.")
        return sanitize_plain_text(value).strip()


class UniversityVerificationSerializer(serializers.Serializer):
    """Submit university email for student verification."""

    email = serializers.EmailField(required=True)
    university_id = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(), required=True
    )
    student_id = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate_student_id(self, value):
        return sanitize_plain_text(value or "")

    def validate_email(self, value):
        from .models import UniversityVerification

        value = (value or "").strip().lower()
        if not value:
            raise serializers.ValidationError("Email is required.")
        try:
            existing = UniversityVerification.objects.get(
                user=self.context["request"].user
            )
            if existing.status == "approved":
                raise serializers.ValidationError(
                    "You are already university verified."
                )
        except UniversityVerification.DoesNotExist:
            pass
        return value

    def validate(self, attrs):
        university = attrs["university_id"]
        email = attrs["email"].lower()
        domain = university.domain.lower().lstrip("@")
        if not email.endswith("@" + domain) and not email.endswith(domain):
            raise serializers.ValidationError(
                {
                    "email": f"Email must be from {university.name} domain (@{university.domain})"
                }
            )
        return attrs
