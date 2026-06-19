from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from esign.dev_reset import dev_reset_lease_signing_session
from esign.models import LeaseSigningSession


class Command(BaseCommand):
    help = (
        "Reset one LeaseSigningSession for local development: clear PDFs/signatures, "
        "audit events, regenerate tokens. Disabled when ESIGN_DEV_RESET_ENABLED is false."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "session_id",
            type=int,
            help="Primary key of esign.LeaseSigningSession",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "ESIGN_DEV_RESET_ENABLED", False):
            raise CommandError(
                "This command is disabled. It only runs when ESIGN_DEV_RESET_ENABLED is True "
                "(development settings, not production or tests)."
            )
        session_id = options["session_id"]
        try:
            session = dev_reset_lease_signing_session(session_id)
        except LeaseSigningSession.DoesNotExist:
            raise CommandError(
                f"No LeaseSigningSession with id={session_id}."
            ) from None
        except RuntimeError as e:
            raise CommandError(str(e)) from e

        self.stdout.write(
            self.style.SUCCESS(
                f"Reset lease signing session id={session.pk} (reservation_id={session.reservation_id})."
            )
        )
        self.stdout.write(
            "Magic-link tokens were regenerated - use the dashboard signing URLs or "
            "admin to copy new links (old links are invalid)."
        )
