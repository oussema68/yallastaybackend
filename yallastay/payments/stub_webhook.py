"""Who may complete a payment via the stub webhook (dev / QA only — never a Stripe substitute)."""

from __future__ import annotations

import hmac
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from django.http import HttpRequest

    from .models import Payment


def may_complete_stub_webhook(
    *,
    request: HttpRequest,
    payment: Payment | None,
    _testing: bool | None = None,
) -> bool:
    """
    Return True if this request may mark ``payment`` completed via stub webhook.

    - Test runner: always allow (CI / Django tests post without auth).
    - Otherwise: allow only if the authenticated user is the **payment owner**, or
      ``STUB_WEBHOOK_SECRET`` is configured and ``X-Stub-Webhook-Secret`` matches (timing-safe).

    ``_testing`` is for unit tests only; do not pass from production code.
    """
    from yallastay.settings import base as settings_base

    testing = settings_base.TESTING if _testing is None else _testing
    if testing:
        return True
    if payment is None:
        return True

    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.id == payment.user_id:
        return True

    configured = (getattr(settings, "STUB_WEBHOOK_SECRET", None) or "").strip()
    if configured:
        got = (request.META.get("HTTP_X_STUB_WEBHOOK_SECRET") or "").strip()
        if got and hmac.compare_digest(got, configured):
            return True

    return False
