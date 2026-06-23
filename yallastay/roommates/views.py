from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsUAEIDVerified
from core.query_window import apply_limit_offset
from .models import RoommateProfile, RoommateInterest
from .serializers import (
    RoommateProfileSerializer,
    RoommateProfileCreateUpdateSerializer,
    RoommateInterestSerializer,
    RoommateInterestCreateSerializer,
    RoommateInterestUpdateSerializer,
)


def _is_tenant_or_student(user):
    try:
        return user.profile.role in ("tenant", "student")
    except Exception:
        return False


def _roommate_profile_queryset():
    return RoommateProfile.objects.select_related(
        "user", "user__profile"
    ).prefetch_related("preferred_areas")


class RoommateProfileView(APIView):
    """
    GET: Own profile JSON when it exists; **200 with body `null`** when the user has not
    created a roommate profile yet (avoids treating a normal state as a client error / log noise).
    POST: Create profile (requires UAE ID verification).
    PUT/PATCH: Update profile (requires UAE ID verification).
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method in ("POST", "PUT", "PATCH"):
            return [IsAuthenticated(), IsUAEIDVerified()]
        return [IsAuthenticated()]

    def _check_role(self, request):
        if not _is_tenant_or_student(request.user):
            return Response(
                {
                    "detail": "Roommate features are for tenants and verified students only."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def get(self, request):
        err = self._check_role(request)
        if err:
            return err
        try:
            profile = _roommate_profile_queryset().get(user=request.user)
            return Response(RoommateProfileSerializer(profile).data)
        except RoommateProfile.DoesNotExist:
            return Response(None, status=status.HTTP_200_OK)

    def post(self, request):
        err = self._check_role(request)
        if err:
            return err
        if hasattr(request.user, "roommate_profile"):
            return Response(
                {"detail": "Profile already exists. Use PATCH to update."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = RoommateProfileCreateUpdateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        profile = _roommate_profile_queryset().get(pk=request.user.roommate_profile.pk)
        return Response(
            RoommateProfileSerializer(profile).data, status=status.HTTP_201_CREATED
        )

    def put(self, request):
        return self._update(request)

    def patch(self, request):
        return self._update(request)

    def _update(self, request):
        err = self._check_role(request)
        if err:
            return err
        try:
            profile = request.user.roommate_profile
        except RoommateProfile.DoesNotExist:
            return Response(
                {"detail": "No profile. Create one first."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = RoommateProfileCreateUpdateSerializer(
            profile, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        profile = _roommate_profile_queryset().get(pk=profile.pk)
        return Response(RoommateProfileSerializer(profile).data)


class RoommateSearchView(APIView):
    """
    GET: Search roommate profiles (others who are ``is_looking``). Requires UAE ID verification.

    Query params:
    - ``area``: preferred area **slug** (e.g. ``dubai-marina``) or numeric **area id**.
    - ``budget_max``: match profiles whose ``budget_min`` is at most this value.
    - ``budget_min``: match profiles with no max or ``budget_max`` at least this value.
    - ``move_in_before``: ISO date (YYYY-MM-DD); include profiles with null move-in or move-in on/before this date.
    - ``age_min``, ``age_max``, ``sex``: filter on renter profile demographics.
    """

    permission_classes = [IsAuthenticated, IsUAEIDVerified]

    def get(self, request):
        if not _is_tenant_or_student(request.user):
            return Response(
                {
                    "detail": "Roommate features are for tenants and verified students only."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        profiles = (
            RoommateProfile.objects.filter(is_looking=True)
            .exclude(user=request.user)
            .prefetch_related("preferred_areas")
            .select_related("user", "user__profile")
        )

        area_param = (request.query_params.get("area") or "").strip()
        if area_param:
            if area_param.isdigit():
                profiles = profiles.filter(
                    preferred_areas__id=int(area_param)
                ).distinct()
            else:
                profiles = profiles.filter(preferred_areas__slug=area_param).distinct()

        budget_max = request.query_params.get("budget_max")
        if budget_max:
            try:
                profiles = profiles.filter(budget_min__lte=float(budget_max))
            except (ValueError, TypeError):
                pass
        budget_min = request.query_params.get("budget_min")
        if budget_min:
            try:
                profiles = profiles.filter(
                    Q(budget_max__isnull=True) | Q(budget_max__gte=float(budget_min))
                )
            except (ValueError, TypeError):
                pass

        move_in_before = request.query_params.get("move_in_before")
        if move_in_before:
            d = parse_date(move_in_before.strip())
            if d:
                profiles = profiles.filter(
                    Q(move_in_date__isnull=True) | Q(move_in_date__lte=d)
                )

        age_min = request.query_params.get("age_min")
        if age_min:
            try:
                profiles = profiles.filter(user__profile__age__gte=int(age_min))
            except (ValueError, TypeError):
                pass
        age_max = request.query_params.get("age_max")
        if age_max:
            try:
                profiles = profiles.filter(user__profile__age__lte=int(age_max))
            except (ValueError, TypeError):
                pass
        sex = request.query_params.get("sex")
        if sex:
            profiles = profiles.filter(user__profile__sex=sex)

        profiles = apply_limit_offset(
            profiles.order_by("-created_at"),
            request,
            default_limit=100,
            max_limit=200,
        )
        serializer = RoommateProfileSerializer(profiles, many=True)
        return Response(serializer.data)


class RoommateInterestView(APIView):
    """
    POST: Express interest in a roommate (requires UAE ID verification).
    """

    permission_classes = [IsAuthenticated, IsUAEIDVerified]

    def post(self, request):
        if not _is_tenant_or_student(request.user):
            return Response(
                {
                    "detail": "Roommate features are for tenants and verified students only."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = RoommateInterestCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        to_user = serializer.validated_data["to_user_id"]
        message = serializer.validated_data.get("message", "")

        interest, created = RoommateInterest.objects.get_or_create(
            from_user=request.user, to_user=to_user, defaults={"message": message}
        )
        if not created:
            return Response(
                {"detail": "Interest already expressed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            RoommateInterestSerializer(interest).data, status=status.HTTP_201_CREATED
        )


class RoommateInterestListView(APIView):
    """GET: List interests sent and received."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_tenant_or_student(request.user):
            return Response(
                {
                    "detail": "Roommate features are for tenants and verified students only."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        sent = (
            RoommateInterest.objects.filter(from_user=request.user)
            .select_related("to_user")
            .order_by("-created_at")
        )
        received = (
            RoommateInterest.objects.filter(to_user=request.user)
            .select_related("from_user")
            .order_by("-created_at")
        )
        sent = apply_limit_offset(
            sent,
            request,
            default_limit=100,
            max_limit=200,
        )
        received = apply_limit_offset(
            received,
            request,
            default_limit=100,
            max_limit=200,
        )
        return Response(
            {
                "sent": RoommateInterestSerializer(sent, many=True).data,
                "received": RoommateInterestSerializer(received, many=True).data,
            }
        )


class RoommateInterestDetailView(APIView):
    """PATCH: Accept/decline received interest (to_user only)."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        interest = get_object_or_404(
            RoommateInterest.objects.select_related("from_user", "to_user"), pk=pk
        )
        if interest.to_user != request.user:
            return Response(
                {"detail": "Only the recipient can accept or decline."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if interest.status != "pending":
            return Response(
                {"detail": "Interest already resolved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = RoommateInterestUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        interest.status = ser.validated_data["status"]
        interest.save()
        return Response(RoommateInterestSerializer(interest).data)
