"""
One-shot demo DB setup for Railway / staging: migrate + core + lifestyle + demo seeds.
Prefer CI + documented curl for public URL smoke tests; use this instead of shell wrappers.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Run migrate (unless skipped) then seed_core, seed_lifestyle, seed_demo. "
        "Use from Railway shell once per fresh Postgres; re-runs may hit unique constraints."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-migrate",
            action="store_true",
            help="Skip migrate if release phase already applied migrations.",
        )

    def handle(self, *args, **options):
        if not options["skip_migrate"]:
            self.stdout.write("Running migrate --noinput...")
            call_command("migrate", "--noinput")

        self.stdout.write("Running seed_core...")
        call_command("seed_core")

        self.stdout.write("Running seed_lifestyle...")
        call_command("seed_lifestyle")

        self.stdout.write("Running seed_demo...")
        call_command("seed_demo")

        self.stdout.write(self.style.SUCCESS("bootstrap_demo finished."))
