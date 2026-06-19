"""
Provider webhooks - no JWT; verify Twilio signature when auth token is configured.
"""

import logging
import os

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import SmsMessage

logger = logging.getLogger(__name__)


def _verify_twilio_request(request) -> bool:
    # Dev/tests: allow unsigned POSTs when explicitly enabled (never use in production).
    if os.environ.get("TWILIO_WEBHOOK_INSECURE_OK", "").lower() in ("1", "true", "yes"):
        return True

    token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    if not token:
        return False

    try:
        from twilio.request_validator import RequestValidator  # type: ignore[import-untyped]
    except ImportError:
        return False

    validator = RequestValidator(token)
    signature = request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
    url = request.build_absolute_uri()
    params = request.POST.dict() if request.POST else {}
    return bool(validator.validate(url, params, signature))


@method_decorator(csrf_exempt, name="dispatch")
class TwilioStatusWebhookView(View):
    """
    Twilio status callback (MessageSid, MessageStatus, etc.).

    POST form fields: MessageSid, MessageStatus, To, ...
    """

    def post(self, request, *args, **kwargs):
        if not _verify_twilio_request(request):
            logger.warning("twilio webhook rejected: bad or missing signature")
            return HttpResponse(status=403)

        sid = request.POST.get("MessageSid", "").strip()
        stat = (request.POST.get("MessageStatus") or "").lower()

        status_map = {
            "queued": SmsMessage.STATUS_QUEUED,
            "sending": SmsMessage.STATUS_SENDING,
            "sent": SmsMessage.STATUS_SENT,
            "delivered": SmsMessage.STATUS_DELIVERED,
            "failed": SmsMessage.STATUS_FAILED,
            "undelivered": SmsMessage.STATUS_UNDELIVERED,
        }
        new_status = status_map.get(stat)
        if sid and new_status:
            updated = SmsMessage.objects.filter(provider_message_id=sid).update(
                status=new_status
            )
            if updated:
                logger.info("twilio webhook sid=%s status=%s", sid, new_status)

        # Twilio expects 200 and no body for status callbacks
        return HttpResponse(status=200)
