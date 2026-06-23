from django.urls import path
from .views import (
    ConversationListCreateView,
    ConversationDetailView,
    ConversationUnreadSummaryView,
    MessageListCreateView,
    MessageMarkReadView,
    ConversationMarkAllReadView,
)

urlpatterns = [
    path(
        "conversations/",
        ConversationListCreateView.as_view(),
        name="conversation-list-create",
    ),
    path(
        "conversations/unread-summary/",
        ConversationUnreadSummaryView.as_view(),
        name="conversation-unread-summary",
    ),
    path(
        "conversations/<int:pk>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path(
        "conversations/<int:pk>/messages/",
        MessageListCreateView.as_view(),
        name="message-list-create",
    ),
    path(
        "conversations/<int:pk>/messages/<int:message_id>/read/",
        MessageMarkReadView.as_view(),
        name="message-mark-read",
    ),
    path(
        "conversations/<int:pk>/mark-read/",
        ConversationMarkAllReadView.as_view(),
        name="conversation-mark-read",
    ),
]
