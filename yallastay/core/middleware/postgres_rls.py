"""
PostgreSQL Row Level Security: set app.request_user_id for each request.

Uses a single outer transaction so SET LOCAL applies to all ORM queries in the view.
Only runs when POSTGRES_RLS_ENABLED is true and the DB engine is PostgreSQL.
"""

from __future__ import annotations

from django.conf import settings
from django.db import connection, transaction


class PostgresRLSContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if connection.vendor != "postgresql" or not getattr(
            settings, "POSTGRES_RLS_ENABLED", True
        ):
            return self.get_response(request)

        if hasattr(request, "user") and request.user.is_authenticated:
            uid = str(request.user.pk)
        else:
            uid = ""

        def set_local():
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.request_user_id = %s", [uid])

        # One transaction for the whole request so SET LOCAL is visible to all queries.
        with transaction.atomic():
            set_local()
            return self.get_response(request)
