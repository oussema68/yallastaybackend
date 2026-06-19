import logging

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsUAEIDVerified
from listings.models import ListingImage
from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    ConversationCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
)

logger = logging.getLogger(__name__)


def _conversation_queryset():
    return Conversation.objects.select_related(
        "listing", "listing__area"
    ).prefetch_related(
        "participants",
        "participants__profile",
        Prefetch(
            "listing__images",
            queryset=ListingImage.objects.order_by("order", "id"),
        ),
    )


class ConversationListCreateView(APIView):
    """
    GET: List user's conversations.
    POST: Start renter inquiry on a listing (requires UAE ID verification).
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsUAEIDVerified()]
        return [IsAuthenticated()]

    def get(self, request):
        convos = (
            _conversation_queryset()
            .filter(participants=request.user)
            .order_by("-updated_at")
        )
        serializer = ConversationSerializer(
            convos, many=True, context={"request": request}
        )
        logger.info(
            "messaging.conversation.list: user_id=%s count=%s",
            request.user.id,
            len(serializer.data),
        )
        return Response(serializer.data)

    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.validated_data["listing_id"]
        lister = listing.listed_by

        if lister == request.user:
            return Response(
                {"detail": "Cannot message yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conv = (
            Conversation.objects.filter(
                listing=listing,
                kind=Conversation.KIND_INQUIRY,
            )
            .filter(participants=request.user)
            .filter(participants=lister)
            .distinct()
            .first()
        )

        if not conv:
            conv = Conversation.objects.create(
                listing=listing,
                kind=Conversation.KIND_INQUIRY,
            )
            conv.participants.add(request.user, lister)

        conv = _conversation_queryset().get(pk=conv.pk)

        logger.info(
            "messaging.conversation.create: user_id=%s conversation_id=%s listing_id=%s",
            request.user.id,
            conv.id,
            listing.id,
        )
        return Response(
            ConversationSerializer(conv, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ConversationDetailView(APIView):
    """GET: Conversation detail. User must be participant."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        conv = _conversation_queryset().filter(pk=pk, participants=request.user).first()
        if not conv:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ConversationSerializer(conv, context={"request": request}).data)


class MessageListCreateView(APIView):
    """
    GET: List messages in conversation.
    POST: Send message (UAE ID required for renter inquiries; owner–broker chats allow files).
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_conversation(self, pk):
        return (
            _conversation_queryset()
            .filter(pk=pk, participants=self.request.user)
            .first()
        )

    def get_permissions(self):
        if self.request.method != "POST":
            return [IsAuthenticated()]
        conv = self.get_conversation(self.kwargs.get("pk"))
        if conv and conv.kind == Conversation.KIND_PARTNERSHIP:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsUAEIDVerified()]

    def get(self, request, pk):
        conv = self.get_conversation(pk)
        if not conv:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        messages = conv.messages.select_related("sender").order_by("created_at")
        msg_data = MessageSerializer(
            messages, many=True, context={"request": request}
        ).data
        logger.info(
            "messaging.messages.list: user_id=%s conversation_id=%s message_count=%s",
            request.user.id,
            conv.id,
            len(msg_data),
        )
        return Response(
            {
                "messages": msg_data,
                "conversation": ConversationSerializer(
                    conv, context={"request": request}
                ).data,
            }
        )

    def post(self, request, pk):
        conv = self.get_conversation(pk)
        if not conv:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attachment = serializer.validated_data.get("attachment")
        attachment_name = ""
        if attachment is not None:
            attachment_name = (getattr(attachment, "name", "") or "")[:255]

        msg = Message.objects.create(
            conversation=conv,
            sender=request.user,
            content=serializer.validated_data.get("content") or "",
            attachment=attachment,
            attachment_name=attachment_name,
        )
        conv.updated_at = timezone.now()
        conv.save(update_fields=["updated_at"])

        logger.info(
            "messaging.message.create: user_id=%s conversation_id=%s message_id=%s has_attachment=%s",
            request.user.id,
            conv.id,
            msg.id,
            bool(attachment),
        )
        return Response(
            MessageSerializer(msg, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MessageMarkReadView(APIView):
    """POST: Mark message(s) as read."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk, message_id):
        conv = _conversation_queryset().filter(pk=pk, participants=request.user).first()
        if not conv:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        msg = get_object_or_404(Message, pk=message_id, conversation=conv)
        if msg.sender != request.user and not msg.read_at:
            msg.read_at = timezone.now()
            msg.save(update_fields=["read_at"])
        return Response(MessageSerializer(msg, context={"request": request}).data)


class ConversationMarkAllReadView(APIView):
    """POST: Mark all messages in conversation as read (for current user - messages not from them)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        conv = _conversation_queryset().filter(pk=pk, participants=request.user).first()
        if not conv:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        updated = (
            conv.messages.exclude(sender=request.user)
            .filter(read_at__isnull=True)
            .update(read_at=timezone.now())
        )
        return Response({"marked": updated})
