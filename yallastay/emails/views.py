"""
SendGrid-style event webhook - no JWT.

Production: set ``SENDGRID_WEBHOOK_SECRET`` and send header ``X-Webhook-Secret`` with the same value,
or use SendGrid's official signature verification (extend here).

Dev: set ``SENDGRID_WEBHOOK_INSECURE_OK=true`` to accept unsigned POSTs (tests only).
"""

import json
import logging
import os

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import EmailMessage

logger = logging.getLogger(__name__)


def _webhook_allowed(request) -> bool:
    if os.environ.get("SENDGRID_WEBHOOK_INSECURE_OK", "").lower() in (
        "1",
        "true",
        "yes",
    ):
        return True
    secret = os.environ.get("SENDGRID_WEBHOOK_SECRET", "").strip()
    if secret and request.META.get("HTTP_X_WEBHOOK_SECRET") == secret:
        return True
    return False


@method_decorator(csrf_exempt, name="dispatch")
class SendGridEventWebhookView(View):
    """
    SendGrid Event Webhook (JSON array of events).

    https://docs.sendgrid.com/for-developers/tracking-events/event
    """

    def post(self, request, *args, **kwargs):
        if not _webhook_allowed(request):
            logger.warning("sendgrid webhook rejected")
            return HttpResponse(status=403)

        try:
            events = json.loads(request.body.decode("utf-8") or "[]")
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        if not isinstance(events, list):
            events = [events]

        event_to_status = {
            "delivered": EmailMessage.STATUS_DELIVERED,
            "bounce": EmailMessage.STATUS_BOUNCED,
            "dropped": EmailMessage.STATUS_DROPPED,
            "deferred": EmailMessage.STATUS_SENDING,
            "processed": EmailMessage.STATUS_SENT,
        }

        for ev in events:
            if not isinstance(ev, dict):
                continue
            event_type = (ev.get("event") or "").lower()
            new_status = event_to_status.get(event_type)
            if not new_status:
                continue
            sg_id = str(ev.get("sg_message_id") or ev.get("smtp-id") or "").strip()
            email = (ev.get("email") or "").strip().lower()
            updated = 0
            if sg_id:
                updated = EmailMessage.objects.filter(provider_message_id=sg_id).update(
                    status=new_status
                )
            if not updated and email:
                EmailMessage.objects.filter(
                    to_email=email, status=EmailMessage.STATUS_SENT
                ).update(status=new_status)

        return HttpResponse(status=200)
