"""Unit tests for stub webhook authorization (no Django test client)."""

from unittest.mock import Mock

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, override_settings

from payments.stub_webhook import may_complete_stub_webhook


class StubWebhookPolicyTests(SimpleTestCase):
    def _req(self, *, user=None, header_secret=""):
        r = Mock()
        r.user = user if user is not None else AnonymousUser()
        r.META = {}
        if header_secret:
            r.META["HTTP_X_STUB_WEBHOOK_SECRET"] = header_secret
        return r

    def _payment(self, user_id=42):
        p = Mock()
        p.user_id = user_id
        return p

    @override_settings(DEBUG=False, STUB_WEBHOOK_SECRET="s3cr3t")
    def test_prod_like_secret_match_allows_anonymous(self):
        req = self._req(user=AnonymousUser(), header_secret="s3cr3t")
        self.assertTrue(
            may_complete_stub_webhook(
                request=req, payment=self._payment(99), _testing=False
            )
        )

    @override_settings(DEBUG=False, STUB_WEBHOOK_SECRET="s3cr3t")
    def test_prod_like_wrong_secret_denies(self):
        req = self._req(user=AnonymousUser(), header_secret="wrong")
        self.assertFalse(
            may_complete_stub_webhook(
                request=req, payment=self._payment(1), _testing=False
            )
        )

    @override_settings(DEBUG=True, STUB_WEBHOOK_SECRET="")
    def test_debug_no_secret_denies_anonymous(self):
        req = self._req(user=AnonymousUser())
        self.assertFalse(
            may_complete_stub_webhook(
                request=req, payment=self._payment(1), _testing=False
            )
        )

    @override_settings(DEBUG=True, STUB_WEBHOOK_SECRET="")
    def test_debug_no_secret_allows_owner(self):
        u = Mock()
        u.is_authenticated = True
        u.id = 7
        req = self._req(user=u)
        self.assertTrue(
            may_complete_stub_webhook(
                request=req, payment=self._payment(7), _testing=False
            )
        )
