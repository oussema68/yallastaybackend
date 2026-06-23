"""Small helper for bounded list responses without changing response shape."""

from __future__ import annotations


def apply_limit_offset(
    queryset,
    request,
    *,
    default_limit: int = 100,
    max_limit: int = 200,
):
    """
    Slice a queryset by ``?limit=`` and ``?offset=`` query params.

    - Keeps API responses as plain arrays (no pagination envelope changes).
    - Enforces a ceiling so list endpoints stay bounded under load.
    """
    qp = getattr(request, "query_params", None) or {}
    limit = default_limit
    offset = 0

    raw_limit = qp.get("limit")
    if raw_limit:
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            limit = default_limit
    limit = max(1, min(limit, max_limit))

    raw_offset = qp.get("offset")
    if raw_offset:
        try:
            offset = int(raw_offset)
        except (TypeError, ValueError):
            offset = 0
    offset = max(0, offset)

    return queryset[offset : offset + limit]
