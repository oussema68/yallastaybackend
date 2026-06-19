"""Signed tokens for email verification (invalidates after profile.is_email_verified flips)."""

from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        profile = getattr(user, "profile", None)
        verified = bool(profile and profile.is_email_verified)
        return f"{user.pk}{user.email}{verified}{timestamp}"


email_verification_token_generator = EmailVerificationTokenGenerator()
