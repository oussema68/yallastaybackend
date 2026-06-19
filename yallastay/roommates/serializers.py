from rest_framework import serializers
from django.contrib.auth import get_user_model

from core.text_sanitize import sanitize_plain_text
from core.models import Area
from .models import RoommateProfile, RoommateInterest

User = get_user_model()


class AreaMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ["id", "name", "slug"]


class RoommateProfileSerializer(serializers.ModelSerializer):
    preferred_areas = AreaMinimalSerializer(many=True, read_only=True)
    preferred_area_ids = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), many=True, source="preferred_areas", required=False
    )
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_role = serializers.CharField(source="user.profile.role", read_only=True)
    place_of_work_or_studies = serializers.SerializerMethodField()
    sex = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()

    class Meta:
        model = RoommateProfile
        fields = [
            "id",
            "user",
            "user_email",
            "user_role",
            "place_of_work_or_studies",
            "sex",
            "age",
            "bio",
            "budget_min",
            "budget_max",
            "preferred_areas",
            "preferred_area_ids",
            "move_in_date",
            "lifestyle_preferences",
            "is_looking",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "created_at", "updated_at"]

    def _profile(self, obj):
        try:
            return obj.user.profile
        except Exception:
            return None

    def get_place_of_work_or_studies(self, obj):
        p = self._profile(obj)
        return (p.place_of_work_or_studies or "").strip() or None if p else None

    def get_sex(self, obj):
        p = self._profile(obj)
        return p.sex or None if p else None

    def get_age(self, obj):
        p = self._profile(obj)
        return p.age if p and p.age is not None else None


class RoommateProfileCreateUpdateSerializer(serializers.ModelSerializer):
    preferred_area_ids = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), many=True, required=False
    )
    bio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    lifestyle_preferences = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    budget_min = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    budget_max = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )

    class Meta:
        model = RoommateProfile
        fields = [
            "bio",
            "budget_min",
            "budget_max",
            "preferred_area_ids",
            "move_in_date",
            "lifestyle_preferences",
            "is_looking",
        ]

    def create(self, validated_data):
        area_ids = validated_data.pop("preferred_area_ids", [])
        user = self.context["request"].user
        profile = RoommateProfile.objects.create(user=user, **validated_data)
        profile.preferred_areas.set(area_ids)
        return profile

    def update(self, instance, validated_data):
        area_ids = validated_data.pop("preferred_area_ids", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if area_ids is not None:
            instance.preferred_areas.set(area_ids)
        return instance

    def validate(self, attrs):
        for field in ("bio", "lifestyle_preferences"):
            if field in attrs and attrs[field] is None:
                attrs[field] = ""
            elif field in attrs and attrs[field]:
                attrs[field] = sanitize_plain_text(attrs[field])
        inst = self.instance
        if "budget_min" in attrs:
            bmin = attrs.get("budget_min")
        else:
            bmin = inst.budget_min if inst else None
        if "budget_max" in attrs:
            bmax = attrs.get("budget_max")
        else:
            bmax = inst.budget_max if inst else None
        if bmin is not None and bmax is not None and bmin > bmax:
            raise serializers.ValidationError(
                {
                    "budget_max": "Budget max must be greater than or equal to budget min."
                }
            )
        return attrs


class RoommateInterestSerializer(serializers.ModelSerializer):
    from_user_email = serializers.EmailField(source="from_user.email", read_only=True)
    to_user_email = serializers.EmailField(source="to_user.email", read_only=True)

    class Meta:
        model = RoommateInterest
        fields = [
            "id",
            "from_user",
            "from_user_email",
            "to_user",
            "to_user_email",
            "message",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["from_user", "status", "created_at", "updated_at"]


class RoommateInterestCreateSerializer(serializers.Serializer):
    to_user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    message = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate_message(self, value):
        return sanitize_plain_text(value or "")

    def validate_to_user_id(self, value):
        if value == self.context["request"].user:
            raise serializers.ValidationError("Cannot express interest in yourself.")
        try:
            RoommateProfile.objects.get(user=value, is_looking=True)
        except RoommateProfile.DoesNotExist:
            raise serializers.ValidationError("User is not looking for roommates.")
        return value


class RoommateInterestUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["accepted", "declined"])
