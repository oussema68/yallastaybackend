"""
Development smoke test: one templated email + one templated SMS.

With DEBUG=True, services also log [OUTBOUND EMAIL] / [OUTBOUND SMS] previews.
Default email backend is console - real MIME appears in this process stdout.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from emails.services import send_transactional_email_from_template
from sms.services import send_sms_from_template


class Command(BaseCommand):
    help = "Send one sample email + SMS via seeded templates (dev smoke test)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default="dev-smoke@example.com",
            help="Recipient for welcome template",
        )
        parser.add_argument(
            "--phone",
            default="+971501234567",
            help="Recipient for generic_message SMS",
        )

    def handle(self, *args, **options):
        to_email = options["email"]
        to_phone = options["phone"]
        if not getattr(settings, "DEBUG", False):
            self.stdout.write(
                self.style.WARNING(
                    "DEBUG is False - [OUTBOUND EMAIL]/[OUTBOUND SMS] preview logs are skipped."
                )
            )

        em = send_transactional_email_from_template(
            to_email,
            "welcome",
            {"first_name": "Dev", "email": to_email},
        )
        self.stdout.write(f"EmailMessage id={em.id} status={em.status}")

        sm = send_sms_from_template(
            to_phone,
            "generic_message",
            {"message": "Outbound smoke test (manage.py outbound_smoke)."},
        )
        self.stdout.write(f"SmsMessage id={sm.id} status={sm.status}")

        self.stdout.write(
            self.style.SUCCESS(
                "Done. With DEBUG=True, see [OUTBOUND EMAIL] / [OUTBOUND SMS] in this terminal; "
                "console email backend prints MIME here too."
            )
        )
