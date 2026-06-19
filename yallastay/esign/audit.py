"""UAE-aligned audit trail for lease e-signing (Federal Decree-Law No. 46 of 2021 - identifiable records)."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from django.db import transaction

if TYPE_CHECKING:
    from django.http import HttpRequest

    from esign.models import LeaseSigningAuditEvent, LeaseSigningSession

# Bump when consent wording or legal basis text changes materially.
UAE_ELECTRONIC_CONSENT_VERSION = "AE-ET-46-2021-v1"

# Shown to signers (API + frontends); not legal advice.
UAE_ELECTRONIC_CONSENT_SUMMARY = (
    "By signing electronically, you agree to use electronic records and signatures "
    "under UAE Federal Decree-Law No. 46 of 2021 on Electronic Transactions and Trust Services. "
    "You may download the signed PDF from your dashboard or email when available."
)


def get_client_ip(request: HttpRequest) -> str | None:
    """Best-effort client IP (honours X-Forwarded-For behind reverse proxies)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()[:45]
    ra = request.META.get("REMOTE_ADDR")
    return ra[:45] if ra else None


def token_fingerprint(token: str) -> str:
    """Non-reversible fingerprint for correlating events without storing raw tokens."""
    return hashlib.sha256(f"esign:{token}".encode()).hexdigest()[:16]


def role_for_token(session: LeaseSigningSession, token: str) -> str:
    t = (token or "").strip()
    if session.renter_token == t:
        return "renter"
    if session.lister_token == t:
        return "lister"
    return ""


def party_signing_complete(session: LeaseSigningSession, token: str) -> bool:
    """True if this party has finished all their signature steps (renter/lister timestamps set)."""
    t = (token or "").strip()
    if session.renter_token == t:
        return bool(session.renter_signed_at)
    if session.lister_token == t:
        return bool(session.lister_signed_at)
    return False


def truthy_consent(val: Any) -> bool:
    if val is True:
        return True
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "on")
    return False


@transaction.atomic
def record_lease_sign_audit(
    session: LeaseSigningSession,
    *,
    event_type: str,
    request: HttpRequest | None,
    actor_role: str = "",
    metadata: dict[str, Any] | None = None,
) -> LeaseSigningAuditEvent:
    from esign.models import LeaseSigningAuditEvent

    ip = get_client_ip(request) if request else None
    ua = ""
    if request:
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:2048]
    meta = dict(metadata or {})
    return LeaseSigningAuditEvent.objects.create(
        session=session,
        event_type=event_type,
        actor_role=actor_role or "",
        ip_address=ip,
        user_agent=ua,
        metadata=meta,
    )


def consent_already_recorded_for_role(session: LeaseSigningSession, role: str) -> bool:
    from esign.models import LeaseSigningAuditEvent

    return LeaseSigningAuditEvent.objects.filter(
        session=session,
        event_type=LeaseSigningAuditEvent.EventType.ELECTRONIC_CONSENT_ACCEPTED,
        actor_role=role,
    ).exists()


def consent_required_for_request(
    session: LeaseSigningSession, token: str, role: str
) -> bool:
    """First-time electronic consent for this party on this session (multi-slot: once per party)."""
    if party_signing_complete(session, token):
        return False
    return not consent_already_recorded_for_role(session, role)
