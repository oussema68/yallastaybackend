from django.urls import path
from .views import (
    NotificationListView,
    NotificationMarkReadView,
    NotificationPreferenceListUpdateView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/<int:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
    path(
        "notifications/preferences/",
        NotificationPreferenceListUpdateView.as_view(),
        name="notification-preferences",
    ),
]
