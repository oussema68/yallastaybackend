from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.checkout import initiate_checkout_for_payment
from payments.models import Payment

from .models import (
    LifestylePartner,
    LifestylePlan,
    LifestylePlanBenefit,
    LifestylePlanSection,
    LifestyleSubscription,
    LifestyleSubscriptionPreference,
)
from .serializers import (
    LifestyleInterestFeedbackSerializer,
    LifestylePartnerSerializer,
    LifestylePlanSerializer,
    LifestyleSubscriptionManagementSerializer,
    LifestyleSubscriptionSerializer,
    LifestyleSubscriptionCreateSerializer,
    LifestyleSubscriptionPreferenceSerializer,
)
from .services import cancel_pending_subscription_payment


class IsLifestyleManagementUser(BasePermission):
    """Staff, superuser, or profile flag ``can_manage_lifestyle`` (set in Django admin)."""

    message = "Lifestyle team access required."

    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if getattr(u, "is_staff", False) or getattr(u, "is_superuser", False):
            return True
        try:
            return bool(u.profile.can_manage_lifestyle)
        except Exception:
            return False


class LifestyleManagementPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LifestyleManagementOverviewView(APIView):
    """
    GET: Paginated lifestyle subscriptions + aggregate counts (staff only).
    Query: ``status``; filter by subscription status; ``page``, ``page_size``.
    """

    permission_classes = [IsAuthenticated, IsLifestyleManagementUser]

    def get(self, request):
        qs = (
            LifestyleSubscription.objects.select_related(
                "user", "plan", "reservation", "reservation__listing"
            )
            .prefetch_related(
                Prefetch(
                    "subscription_payments",
                    queryset=Payment.objects.order_by("-created_at"),
                )
            )
            .order_by("-created_at")
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        summary = {
            "total_subscriptions": LifestyleSubscription.objects.count(),
            "by_status": dict(
                LifestyleSubscription.objects.values("status")
                .annotate(c=Count("id"))
                .values_list("status", "c")
            ),
            "by_plan": dict(
                LifestyleSubscription.objects.values("plan__name")
                .annotate(c=Count("id"))
                .values_list("plan__name", "c")
            ),
        }

        paginator = LifestyleManagementPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = LifestyleSubscriptionManagementSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["summary"] = summary
        return response


class LifestylePlanListView(APIView):
    """GET: List all lifestyle plans (Essential, Comfort, Complete)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        benefit_qs = LifestylePlanBenefit.objects.order_by("sort_order", "id")
        section_qs = LifestylePlanSection.objects.order_by(
            "sort_order", "id"
        ).prefetch_related(Prefetch("benefits", queryset=benefit_qs))
        plans = (
            LifestylePlan.objects.filter(is_active=True)
            .order_by("tier")
            .prefetch_related(
                Prefetch("sections", queryset=section_qs),
                "services",
            )
        )
        return Response(LifestylePlanSerializer(plans, many=True).data)


class LifestyleSubscriptionListCreateView(APIView):
    """
    GET: List user's lifestyle subscriptions (includes payment status for each).
    POST: Start a paid subscription: creates a pending subscription + lifestyle payment
    and returns the same checkout payload as POST /api/payments/initiate/ plus ``subscription``.
    Complete payment via Stripe (or stub webhook) to activate the subscription.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        pay_qs = Payment.objects.order_by("-created_at")
        subs = (
            LifestyleSubscription.objects.filter(user=request.user)
            .select_related(
                "plan",
                "reservation",
                "reservation__listing",
                "lifestyle_preferences",
                "lifestyle_preferences__gym_partner",
            )
            .prefetch_related(Prefetch("subscription_payments", queryset=pay_qs))
        )
        return Response(LifestyleSubscriptionSerializer(subs, many=True).data)

    def post(self, request):
        serializer = LifestyleSubscriptionCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        reservation = serializer.validated_data["reservation_id"]
        plan = serializer.validated_data["plan_id"]
        start_date = serializer.validated_data["start_date"]
        end_date = serializer.validated_data.get("end_date") or reservation.end_date

        created_new_sub = False
        payment_created_this_request = False

        sub = LifestyleSubscription.objects.filter(
            reservation=reservation,
            plan=plan,
            user=request.user,
            status="pending_payment",
        ).first()

        if not sub:
            created_new_sub = True
            payment_created_this_request = True
            sub = LifestyleSubscription.objects.create(
                reservation=reservation,
                plan=plan,
                user=request.user,
                start_date=start_date,
                end_date=end_date,
                status="pending_payment",
            )
            payment = Payment.objects.create(
                user=request.user,
                amount=plan.price,
                currency=plan.currency,
                payment_type="lifestyle",
                status="pending",
                reservation=reservation,
                lifestyle_subscription=sub,
                transaction_id="",
            )
        else:
            payment = (
                Payment.objects.filter(
                    lifestyle_subscription=sub,
                    status="pending",
                )
                .order_by("-created_at")
                .first()
            )
            if not payment:
                payment_created_this_request = True
                payment = Payment.objects.create(
                    user=request.user,
                    amount=plan.price,
                    currency=plan.currency,
                    payment_type="lifestyle",
                    status="pending",
                    reservation=reservation,
                    lifestyle_subscription=sub,
                    transaction_id="",
                )

        resp = initiate_checkout_for_payment(payment, user_id=request.user.id)
        if resp.status_code != status.HTTP_201_CREATED:
            if payment_created_this_request:
                payment.delete()
            if created_new_sub:
                sub.delete()
            return resp

        body = dict(resp.data)
        body["subscription"] = LifestyleSubscriptionSerializer(sub).data
        return Response(body, status=resp.status_code)


class LifestyleSubscriptionDetailView(APIView):
    """GET: Subscription detail. PATCH: Update or cancel."""

    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(
            LifestyleSubscription.objects.select_related(
                "plan",
                "reservation",
                "reservation__listing",
                "lifestyle_preferences",
                "lifestyle_preferences__gym_partner",
            ).prefetch_related(
                Prefetch(
                    "subscription_payments",
                    queryset=Payment.objects.order_by("-created_at"),
                )
            ),
            pk=pk,
            user=user,
        )

    def get(self, request, pk):
        sub = self.get_object(pk, request.user)
        return Response(LifestyleSubscriptionSerializer(sub).data)

    def patch(self, request, pk):
        sub = self.get_object(pk, request.user)
        status_val = request.data.get("status")
        if status_val == "cancelled":
            if sub.status == "pending_payment":
                cancel_pending_subscription_payment(sub)
            sub.status = "cancelled"
            sub.save(update_fields=["status", "updated_at"])
        return Response(LifestyleSubscriptionSerializer(sub).data)


class LifestylePartnerListView(APIView):
    """GET: Active partners (gyms, cleaning vendors) for benefit configuration."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = LifestylePartner.objects.filter(is_active=True).order_by(
            "partner_type", "sort_order", "id"
        )
        ptype = request.query_params.get("partner_type")
        if ptype:
            qs = qs.filter(partner_type=ptype)
        return Response(LifestylePartnerSerializer(qs, many=True).data)


class LifestyleSubscriptionPreferencesView(APIView):
    """
    GET/PATCH: Preferences for an **active** subscription (gym choice, cleaning window, notes).
    Creates a preference row on first GET.
    """

    permission_classes = [IsAuthenticated]

    def _get_subscription(self, pk, user):
        sub = get_object_or_404(
            LifestyleSubscription.objects.select_related(
                "plan", "reservation", "reservation__listing"
            ),
            pk=pk,
            user=user,
        )
        if sub.status != "active":
            return None, sub
        return sub, None

    def get(self, request, pk):
        sub, inactive = self._get_subscription(pk, request.user)
        if inactive is not None:
            return Response(
                {
                    "detail": "Preferences are only available for active subscriptions.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        pref, _ = LifestyleSubscriptionPreference.objects.get_or_create(
            subscription=sub
        )
        pref = LifestyleSubscriptionPreference.objects.select_related(
            "gym_partner"
        ).get(pk=pref.pk)
        return Response(LifestyleSubscriptionPreferenceSerializer(pref).data)

    def patch(self, request, pk):
        sub, inactive = self._get_subscription(pk, request.user)
        if inactive is not None:
            return Response(
                {
                    "detail": "Preferences are only available for active subscriptions.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        pref, _ = LifestyleSubscriptionPreference.objects.get_or_create(
            subscription=sub
        )
        serializer = LifestyleSubscriptionPreferenceSerializer(
            pref,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        pref = LifestyleSubscriptionPreference.objects.select_related(
            "gym_partner"
        ).get(pk=pref.pk)
        return Response(LifestyleSubscriptionPreferenceSerializer(pref).data)


class LifestyleInterestFeedbackCreateView(APIView):
    """
    POST: Save coming-soon lifestyle interest (guests or authenticated tenants).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LifestyleInterestFeedbackSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        feedback = serializer.save()
        return Response(
            LifestyleInterestFeedbackSerializer(feedback).data,
            status=status.HTTP_201_CREATED,
        )
