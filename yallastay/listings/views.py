from django.db import transaction
from django.db.models import Exists, Max, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from accounts.permissions import user_has_uae_id_verified
from core.text_sanitize import sanitize_plain_text
from notifications.services import notify_user

from .emails import send_listing_created_email
from .filters import ListingFilter
from .models import Favorite, Listing, ListingImage, ListingOwnerInvite
from .notifications import notify_listing_published
from .permissions import IsLandlordOrRealtor
from .serializers import (
    FavoriteCreateSerializer,
    FavoriteSerializer,
    ListingListSerializer,
    ListingSerializer,
)
from .assignment import (
    reviewing_broker_id,
    reviewing_broker_user,
    user_is_reviewing_broker,
)
from .emails_assignment import send_owner_invite_email
from .notifications import notify_owner_invite_sent
from .owner_invites import OwnerInviteError, accept_listing_owner_invite

LISTING_MAX_IMAGES = 30


def _sanitize_owner_verification_note(raw) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    return sanitize_plain_text(s)[:2000]


def _notify_owner_verification_submitter(listing, *, title: str, body: str) -> None:
    """Notify the landlord who owns verification: assigned property_owner, else self-listed lister."""
    link = f"/property/{listing.pk}/"
    user = listing.property_owner if listing.property_owner_id else listing.listed_by
    if user:
        notify_user(user, "listing", title, body[:2000], link=link)


def _completed_lease_signing_exists():
    """Subquery: this listing has a reservation whose lease signing session is completed."""
    from esign.models import LeaseSigningSession

    return LeaseSigningSession.objects.filter(
        reservation__listing_id=OuterRef("pk"),
        status="completed",
    )


def _public_browse_queryset(qs):
    """
    Search / home / anonymous browse: active listings that are not rented out.
    Excludes leased=True and any listing with a fully signed lease session (covers missed flags).
    """
    return (
        qs.filter(status="active")
        .filter(leased=False)
        .annotate(
            _has_completed_lease_signing=Exists(_completed_lease_signing_exists())
        )
        .filter(_has_completed_lease_signing=False)
    )


def _send_listing_after_commit(user, listing_id: int) -> None:
    listing = Listing.objects.filter(pk=listing_id).first()
    if not listing:
        return
    total = Listing.objects.filter(listed_by=user).count()
    is_first = total == 1
    send_listing_created_email(user, listing, is_first=is_first)
    notify_listing_published(user, listing, is_first=is_first)


class ListingViewSet(viewsets.ModelViewSet):
    queryset = (
        Listing.objects.filter(status="active")
        .select_related(
            "area",
            "listed_by",
            "property_owner",
            "title_deed_document",
            "assigned_realtor__realtor_profile",
            "owner_verification_by",
        )
        .prefetch_related("images")
    )
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = [IsAuthenticatedOrReadOnly, IsLandlordOrRealtor]
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]
    filterset_class = ListingFilter
    ordering_fields = ["price", "created_at"]
    search_fields = ["title", "description", "address"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ListingListSerializer
        return ListingSerializer

    def get_queryset(self):
        qs = Listing.objects.select_related(
            "area",
            "listed_by",
            "property_owner",
            "title_deed_document",
            "assigned_realtor__realtor_profile",
            "owner_verification_by",
        ).prefetch_related("images")
        user = self.request.user
        active = Q(status="active")

        if user.is_authenticated:
            try:
                if user.profile.role in ("landlord", "realtor"):
                    mine = self.request.query_params.get("mine")
                    if mine:
                        # Landlords: listings they created OR where they are the property owner
                        # (e.g. unit listed by a realtor). Realtors: only listings they listed.
                        if user.profile.role == "landlord":
                            return qs.filter(
                                Q(listed_by=user) | Q(property_owner=user)
                            ).filter(active)
                        # Realtor: listings they published OR listings where an owner assigned them to help
                        return qs.filter(
                            Q(listed_by=user) | Q(assigned_realtor=user)
                        ).filter(active)
            except Exception:
                pass

            listing_access_actions = (
                "retrieve",
                "request_owner_verification",
                "approve_owner_verification",
                "reject_owner_verification",
            )
            if self.action in listing_access_actions:
                uid = user.id
                completed = _completed_lease_signing_exists()
                return (
                    qs.filter(active)
                    .annotate(_completed_signing=Exists(completed))
                    .filter(
                        Q(listed_by_id=uid)
                        | Q(property_owner_id=uid)
                        | Q(assigned_realtor_id=uid)
                        | Q(reservations__user_id=uid)
                        | (Q(leased=False) & Q(_completed_signing=False))
                    )
                    .distinct()
                )

            if self.action in (
                "update",
                "partial_update",
                "destroy",
                "delete_image",
                "interested",
                "invite_owner",
            ):
                try:
                    if user.profile.role in ("landlord", "realtor"):
                        # Lister, assigned realtor browse-visible, or property owner (deed only) OR browse-visible
                        public_pks = _public_browse_queryset(qs).values_list(
                            "pk", flat=True
                        )
                        return qs.filter(
                            Q(listed_by_id=user.id)
                            | Q(property_owner_id=user.id)
                            | Q(assigned_realtor_id=user.id)
                            | Q(pk__in=public_pks)
                        ).distinct()
                except Exception:
                    pass

        # Public browse + authenticated search (no mine): hide rented / fully signed leases
        return _public_browse_queryset(qs)

    def perform_create(self, serializer):
        serializer.save(listed_by=self.request.user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Accept JSON or multipart form; optional ``images`` file list (max 30)."""
        images = request.FILES.getlist("images")
        if len(images) > LISTING_MAX_IMAGES:
            return Response(
                {
                    "images": [
                        f"Maximum {LISTING_MAX_IMAGES} images per listing (received {len(images)})."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.save(listed_by=request.user)
        for i, f in enumerate(images):
            ListingImage.objects.create(listing=listing, image=f, order=i)
        output = ListingSerializer(listing, context={"request": request})
        headers = self.get_success_headers(output.data)
        transaction.on_commit(
            lambda u=request.user, lid=listing.pk: _send_listing_after_commit(u, lid)
        )
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        """JSON or multipart; optional ``images`` file list appends photos (max 30 total)."""
        images = request.FILES.getlist("images")
        listing = self.get_object()
        uid = request.user.id
        is_assigned_realtor_only = (
            listing.assigned_realtor_id == uid and listing.listed_by_id != uid
        )
        if is_assigned_realtor_only:
            if images:
                return Response(
                    {"detail": "Only the listing publisher can add or replace photos."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            allowed = {"trakheesi_permit_number"}
            incoming = set(request.data.keys())
            if incoming - allowed:
                return Response(
                    {
                        "detail": "As the assigned broker you may only update the Trakheesi "
                        "Advertising Permit number (issued via DLD Trakheesi) on this listing."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            payload = {k: request.data[k] for k in allowed if k in request.data}
            kwargs.setdefault("partial", True)
            serializer = self.get_serializer(listing, data=payload, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            listing = serializer.instance
            listing.refresh_from_db()
            output = ListingSerializer(listing, context={"request": request})
            return Response(output.data)

        is_property_owner_only = (
            listing.property_owner_id == uid and listing.listed_by_id != uid
        )
        if is_property_owner_only:
            if images:
                return Response(
                    {"detail": "Only the listing publisher can add or replace photos."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            allowed = {"title_deed_document", "title_deed_reference"}
            incoming = set(request.data.keys())
            if incoming - allowed:
                return Response(
                    {
                        "detail": "As the assigned property owner you may only update the title deed "
                        "document and reference on this listing."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            payload = {k: request.data[k] for k in allowed if k in request.data}
            kwargs.setdefault("partial", True)
            serializer = self.get_serializer(listing, data=payload, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            listing = serializer.instance
            listing.refresh_from_db()
            if listing.owner_verification_status == "rejected":
                Listing.objects.filter(pk=listing.pk).update(
                    owner_verification_status="none",
                    owner_verification_note="",
                    owner_verification_by=None,
                    owner_verification_at=None,
                )
                listing.refresh_from_db()
            output = ListingSerializer(listing, context={"request": request})
            return Response(output.data)

        existing = listing.images.count()
        if existing + len(images) > LISTING_MAX_IMAGES:
            return Response(
                {
                    "images": [
                        f"Maximum {LISTING_MAX_IMAGES} images per listing "
                        f"(have {existing}, adding {len(images)} would exceed the limit)."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        kwargs.setdefault("partial", True)
        serializer = self.get_serializer(listing, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        listing = serializer.instance
        max_order = listing.images.aggregate(m=Max("order"))["m"]
        if max_order is None:
            max_order = -1
        for i, f in enumerate(images):
            ListingImage.objects.create(
                listing=listing, image=f, order=max_order + 1 + i
            )
        listing.refresh_from_db()
        output = ListingSerializer(listing, context={"request": request})
        return Response(output.data)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"images/(?P<image_id>\d+)",
    )
    def delete_image(self, request, pk=None, image_id=None):
        """Remove one gallery image; only the lister may delete."""
        listing = self.get_object()
        if listing.listed_by_id != request.user.id:
            return Response(
                {"detail": "Only the listing owner can remove images."},
                status=status.HTTP_403_FORBIDDEN,
            )
        img = get_object_or_404(ListingImage, pk=image_id, listing=listing)
        img.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsLandlordOrRealtor],
        url_path="request-owner-verification",
    )
    def request_owner_verification(self, request, pk=None):
        """
        Landlord (lister or assigned property_owner): after UAE ID is approved and the listing has a
        title deed, request review from the assigned verified realtor.
        """
        listing = self.get_object()
        uid = request.user.id
        if listing.listed_by_id != uid and listing.property_owner_id != uid:
            return Response(
                {
                    "detail": "Only the lister or assigned property owner can request verification."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            if request.user.profile.role != "landlord":
                return Response(
                    {
                        "detail": "Only landlord accounts can request property-owner verification."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        except Exception:
            return Response(
                {
                    "detail": "Only landlord accounts can request property-owner verification."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not user_has_uae_id_verified(request.user):
            return Response(
                {
                    "detail": "Complete Emirates ID verification (Get verified) before requesting a realtor review."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not listing.title_deed_document_id:
            return Response(
                {
                    "detail": "Link a title deed document and reference on this listing before requesting review."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        broker_id = reviewing_broker_id(listing)
        if not broker_id:
            return Response(
                {
                    "detail": (
                        "Link a verified broker before requesting review. "
                        "Landlords: choose an assigned realtor on the listing. "
                        "If your broker published the ad, they are notified automatically."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if listing.owner_verification_status == "pending":
            return Response(
                {"detail": "A verification request is already pending."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        Listing.objects.filter(pk=listing.pk).update(
            owner_verification_status="pending",
            owner_verification_note="",
            owner_verification_by=None,
            owner_verification_at=None,
        )
        listing.refresh_from_db()
        broker = reviewing_broker_user(listing)
        if broker:
            notify_user(
                broker,
                "listing",
                "Owner verification requested",
                f'"{listing.title}": the owner asked you to review the title deed and documents.',
                link=f"/property/{listing.pk}/",
            )
        return Response(
            ListingSerializer(listing, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsLandlordOrRealtor],
        url_path="approve-owner-verification",
    )
    def approve_owner_verification(self, request, pk=None):
        """Assigned verified realtor: approve title deed / owner documents for this listing."""
        listing = self.get_object()
        if not user_is_reviewing_broker(request.user, listing):
            return Response(
                {"detail": "Only the listing broker can approve owner verification."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            if request.user.profile.role != "realtor":
                return Response(
                    {"detail": "Only realtor accounts can complete this review."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except Exception:
            return Response(
                {"detail": "Only realtor accounts can complete this review."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if listing.owner_verification_status != "pending":
            return Response(
                {"detail": "No pending owner verification request for this listing."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        note = _sanitize_owner_verification_note(request.data.get("note", ""))
        Listing.objects.filter(pk=listing.pk).update(
            owner_verification_status="approved",
            owner_verification_by_id=request.user.id,
            owner_verification_note=note,
            owner_verification_at=timezone.now(),
        )
        listing.refresh_from_db()
        body = (
            f'Your documents for "{listing.title}" were approved by the assigned realtor.'
            + (f" Note: {note}" if note else "")
        )
        _notify_owner_verification_submitter(
            listing,
            title="Owner documents approved",
            body=body,
        )
        return Response(
            ListingSerializer(listing, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsLandlordOrRealtor],
        url_path="reject-owner-verification",
    )
    def reject_owner_verification(self, request, pk=None):
        """Assigned verified realtor: refuse owner documents with a reason shown to the owner."""
        listing = self.get_object()
        if not user_is_reviewing_broker(request.user, listing):
            return Response(
                {"detail": "Only the listing broker can reject owner verification."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            if request.user.profile.role != "realtor":
                return Response(
                    {"detail": "Only realtor accounts can complete this review."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except Exception:
            return Response(
                {"detail": "Only realtor accounts can complete this review."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if listing.owner_verification_status != "pending":
            return Response(
                {"detail": "No pending owner verification request for this listing."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = (request.data.get("reason") or "").strip()
        if len(reason) < 10:
            return Response(
                {
                    "reason": [
                        "Provide a clear refusal reason (at least 10 characters) for the owner."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        note = _sanitize_owner_verification_note(reason)
        Listing.objects.filter(pk=listing.pk).update(
            owner_verification_status="rejected",
            owner_verification_by_id=request.user.id,
            owner_verification_note=note,
            owner_verification_at=timezone.now(),
        )
        listing.refresh_from_db()
        _notify_owner_verification_submitter(
            listing,
            title="Owner documents not approved",
            body=f'Your documents for "{listing.title}" were not approved. Reason: {note}',
        )
        return Response(
            ListingSerializer(listing, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="interested",
    )
    def interested(self, request, pk=None):
        """Users who saved this listing (Interested list). Only the lister may view."""
        listing = self.get_object()
        if listing.listed_by_id != request.user.id:
            return Response(
                {"detail": "Only the listing owner can view interested users."},
                status=status.HTTP_403_FORBIDDEN,
            )
        favs = (
            Favorite.objects.filter(listing=listing)
            .select_related("user")
            .order_by("-created_at")
        )
        data = []
        for f in favs:
            u = f.user
            data.append(
                {
                    "favorite_id": f.id,
                    "created_at": f.created_at,
                    "user": {
                        "id": u.id,
                        "email": u.email,
                        "first_name": u.first_name or "",
                        "last_name": u.last_name or "",
                    },
                }
            )
        return Response(data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsLandlordOrRealtor],
        url_path="invite-owner",
    )
    def invite_owner(self, request, pk=None):
        """
        Realtor-only: email a prospective landlord with a signup link and invite token.
        When they register (or accept while signed in), they are linked as ``property_owner``.
        """
        import uuid

        listing = self.get_object()
        if listing.listed_by_id != request.user.id:
            return Response(
                {"detail": "Only the listing creator can send this invite."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            role = request.user.profile.role
        except Exception:
            role = None
        if role != "realtor":
            return Response(
                {"detail": "Only realtor accounts can invite a property owner."},
                status=status.HTTP_403_FORBIDDEN,
            )
        email = (request.data.get("email") or "").strip().lower()
        if not email or "@" not in email:
            return Response(
                {"email": ["Enter a valid email address."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ListingOwnerInvite.objects.filter(listing=listing, email__iexact=email).delete()
        invite = ListingOwnerInvite.objects.create(
            listing=listing,
            email=email,
            invited_by=request.user,
            token=uuid.uuid4().hex,
        )
        send_owner_invite_email(
            to_email=email,
            listing=listing,
            realtor=request.user,
            invite_token=invite.token,
        )
        notify_owner_invite_sent(listing, invite_email=email)
        return Response(
            {
                "detail": "Invitation email sent.",
                "invite_token": invite.token,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="accept-owner-invite",
    )
    def accept_owner_invite(self, request):
        """Landlord accepts an email invite and is linked as property owner on the listing."""
        token = (request.data.get("token") or "").strip()
        if not token:
            return Response(
                {"token": ["Invite token is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            listing = accept_listing_owner_invite(token=token, user=request.user)
        except OwnerInviteError as exc:
            return Response({"detail": exc.message}, status=exc.status)
        return Response(
            ListingSerializer(listing, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticatedOrReadOnly()]
        return [IsAuthenticatedOrReadOnly(), IsLandlordOrRealtor()]


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related(
            "listing", "listing__area"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return FavoriteCreateSerializer
        return FavoriteSerializer

    def create(self, request, *args, **kwargs):
        serializer = FavoriteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.validated_data["listing"]
        fav, created = Favorite.objects.get_or_create(
            user=request.user, listing=listing
        )
        return Response(
            FavoriteSerializer(fav).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
