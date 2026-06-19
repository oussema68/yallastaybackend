"""
Inspect Row Level Security on PostgreSQL public tables.

SQLite: prints that RLS does not apply.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "List RLS flags for public tables (PostgreSQL only)."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stdout.write(
                self.style.WARNING(
                    f"Database engine is {connection.vendor!r}, not PostgreSQL - "
                    "RLS is not applicable here (dev often uses SQLite)."
                )
            )
            return

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.relname,
                       c.relrowsecurity AS rls_enabled,
                       c.relforcerowsecurity AS rls_forced
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                ORDER BY c.relname
                """)
            rows = cursor.fetchall()

        if not rows:
            self.stdout.write("No public tables found.")
            return

        self.stdout.write(
            "public tables: relrowsecurity = RLS enabled, "
            "relforcerowsecurity = FORCE ROW LEVEL SECURITY\n"
        )
        for name, rls_enabled, rls_forced in rows:
            flags = []
            if rls_enabled:
                flags.append("RLS")
            if rls_forced:
                flags.append("FORCE")
            flag_s = ", ".join(flags) if flags else "off"
            self.stdout.write(f"  {name}: {flag_s}")

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
                FROM pg_policies
                WHERE schemaname = 'public'
                ORDER BY tablename, policyname
                """)
            policies = cursor.fetchall()

        self.stdout.write("")
        if not policies:
            self.stdout.write(
                self.style.WARNING(
                    "No RLS policies in public schema - row access is not restricted "
                    "at the database layer (Django/DRF rules apply in the app)."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"{len(policies)} policy/policies in public:")
        )
        for row in policies:
            self.stdout.write(f"  {row[1]}.{row[2]} ({row[5]})")
