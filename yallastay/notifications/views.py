from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer


class NotificationListView(APIView):
    """GET: List current user's notifications."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by(
            "-created_at"
        )
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class NotificationMarkReadView(APIView):
    """PATCH: Mark notification as read."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.read = True
        notification.save(update_fields=["read"])
        return Response(NotificationSerializer(notification).data)


class NotificationPreferenceListUpdateView(APIView):
    """GET: List preferences. PATCH: Update preferences."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs = NotificationPreference.objects.filter(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs, many=True)
        return Response(serializer.data)

    def patch(self, request):
        # Accept list of {channel, notification_type, enabled}
        data = request.data
        if isinstance(data, list):
            updated = []
            for item in data:
                channel = item.get("channel")
                notification_type = item.get("notification_type", "general")
                enabled = item.get("enabled", True)
                if channel:
                    pref, _ = NotificationPreference.objects.update_or_create(
                        user=request.user,
                        channel=channel,
                        notification_type=notification_type,
                        defaults={"enabled": enabled},
                    )
                    updated.append(pref)
            return Response(NotificationPreferenceSerializer(updated, many=True).data)
        # Single object
        channel = data.get("channel")
        notification_type = data.get("notification_type", "general")
        enabled = data.get("enabled", True)
        if channel:
            pref, _ = NotificationPreference.objects.update_or_create(
                user=request.user,
                channel=channel,
                notification_type=notification_type,
                defaults={"enabled": enabled},
            )
            return Response(NotificationPreferenceSerializer(pref).data)
        return Response(
            {"detail": "channel required"}, status=status.HTTP_400_BAD_REQUEST
        )
