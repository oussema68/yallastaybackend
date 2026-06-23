from urllib.parse import unquote

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.conf import settings
from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .email_verification import send_email_verification
from .password_reset import send_password_reset_email
from .serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
    UserProfileUpdateSerializer,
)
from .tokens import email_verification_token_generator
from core.background import run_side_effect
from notifications.services import notify_user

User = get_user_model()


class CustomTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["token"] = data["access"]  # Frontend expects 'token'
        return data


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_refresh"


class LogoutView(APIView):
    """Logout: blacklist refresh token (BoilerPlate pattern)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response(
                {"message": "Logged out successfully."}, status=status.HTTP_200_OK
            )
        except Exception:
            return Response({"message": "Logged out."}, status=status.HTTP_200_OK)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user_id = user.pk

        def after_signup():
            signup_user = User.objects.get(pk=user_id)
            run_side_effect(
                "send_email_verification_after_signup",
                send_email_verification,
                signup_user,
            )
            notify_user(
                signup_user,
                "welcome",
                "Welcome to Yallastay",
                "Explore listings, verify your Emirates ID, and find your next home in Dubai.",
                link="/dashboard",
            )

        transaction.on_commit(after_signup)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "token": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    """Get or update current user profile (BoilerPlate pattern: GET/PUT/PATCH)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                UserSerializer(request.user).data, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)


class VerifyEmailView(APIView):
    """
    GET /api/auth/verify-email/<uidb64>/<token>/ - marks profile email as verified.

    Also supports query params (recommended for emails; avoids path encoding issues with ``=``):
    GET /api/auth/verify-email/?uid=<uidb64>&token=<token>&redirect=1
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_verify_email"

    def get(self, request, uidb64=None, token=None):
        uidb64 = uidb64 or request.GET.get("uid") or request.GET.get("uidb64")
        token = token or request.GET.get("token")
        if not uidb64 or not token:
            return Response(
                {"detail": "Invalid verification link."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        uidb64 = unquote(uidb64.strip())
        token = unquote(token.strip())
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.select_related("profile").get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response(
                {"detail": "Invalid verification link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = getattr(user, "profile", None)
        if not profile:
            return Response(
                {"detail": "Invalid verification link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        redirect_url = self._redirect_success()
        if profile.is_email_verified:
            if request.GET.get("redirect") == "1":
                return HttpResponseRedirect(redirect_url)
            return Response(
                {
                    "detail": "Email already verified.",
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_200_OK,
            )

        if not email_verification_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired verification link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile.is_email_verified = True
        profile.email_verified_at = timezone.now()
        profile.save(
            update_fields=["is_email_verified", "email_verified_at", "updated_at"]
        )
        user.refresh_from_db()
        notify_user(
            user,
            "email_verified",
            "Email verified",
            "Your account email is confirmed. Complete Emirates ID verification to unlock messaging and rentals.",
            link="/verify",
        )

        if request.GET.get("redirect") == "1":
            return HttpResponseRedirect(redirect_url)
        return Response(
            {"detail": "Email verified.", "user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )

    def _redirect_success(self):
        base = (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
        return f"{base}/?email_verified=1"


class ResendVerificationEmailView(APIView):
    """POST /api/auth/verify-email/resend/ - authenticated users only."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_resend_verification"

    def post(self, request):
        user = request.user
        try:
            profile = user.profile
        except Exception:
            return Response(
                {"detail": "Profile not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if profile.is_email_verified:
            return Response(
                {"detail": "Email already verified."},
                status=status.HTTP_200_OK,
            )
        run_side_effect(
            "send_email_verification_resend",
            send_email_verification,
            user,
        )
        return Response(
            {"detail": "Verification email sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password-reset/: request reset email (same response whether or not email exists).
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw = serializer.validated_data["email"].strip()
        email = BaseUserManager.normalize_email(raw)
        user = User.objects.filter(email__iexact=email).first()
        if user and user.is_active:
            run_side_effect(
                "send_password_reset_email",
                send_password_reset_email,
                user,
            )
        return Response(
            {
                "detail": "If an account exists for this email, you will receive password reset instructions."
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """POST /api/auth/password-reset/confirm/: uid, token, new_password (from email link)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_password_reset_confirm"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["_user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response(
            {"detail": "Password has been reset."},
            status=status.HTTP_200_OK,
        )
