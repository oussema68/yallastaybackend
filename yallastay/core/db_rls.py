"""
Row Level Security helpers (PostgreSQL only).

Call set_request_user_id_for_rls() inside transaction.atomic() before ORM queries that
must satisfy RLS when the HTTP middleware did not set the session (e.g. Stripe webhooks).
"""

from __future__ import annotations

from django.db import connection


def set_request_user_id_for_rls(user_id: int | None) -> None:
    """
    SET LOCAL app.request_user_id for the current DB transaction.
    Must run inside the same transaction.atomic() as subsequent queries.
    """
    if connection.vendor != "postgresql":
        return
    uid = "" if user_id is None else str(int(user_id))
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL app.request_user_id = %s", [uid])
