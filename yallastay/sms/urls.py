from django.urls import path

from .views import TwilioStatusWebhookView

urlpatterns = [
    path(
        "webhooks/twilio/status/",
        TwilioStatusWebhookView.as_view(),
        name="sms-twilio-status-webhook",
    ),
]
