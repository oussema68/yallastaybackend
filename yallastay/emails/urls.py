from django.urls import path

from .views import SendGridEventWebhookView

urlpatterns = [
    path(
        "webhooks/sendgrid/events/",
        SendGridEventWebhookView.as_view(),
        name="emails-sendgrid-events-webhook",
    ),
]
