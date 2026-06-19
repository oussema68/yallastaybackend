from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings


class DevResetEsignSessionCommandTests(TestCase):
    @override_settings(ESIGN_DEV_RESET_ENABLED=False)
    def test_command_refused_when_disabled(self):
        with self.assertRaises(CommandError) as ctx:
            call_command("dev_reset_esign_session", "1")
        self.assertIn("disabled", str(ctx.exception).lower())
