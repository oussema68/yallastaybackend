from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendVerificationEmailView,
    ThrottledTokenRefreshView,
    VerifyEmailView,
)
from .overview_views import AccountOverviewView
from .public_profile_views import PublicUserProfileView
from .verified_realtors_views import VerifiedRealtorsListView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
    path(
        "password-reset/",
        PasswordResetRequestView.as_view(),
        name="password_reset_request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("me/", MeView.as_view(), name="me"),
    path("account-overview/", AccountOverviewView.as_view(), name="account-overview"),
    path(
        "verified-realtors/",
        VerifiedRealtorsListView.as_view(),
        name="verified-realtors",
    ),
    path(
        "users/<int:pk>/public-profile/",
        PublicUserProfileView.as_view(),
        name="public-profile",
    ),
    path(
        "verify-email/resend/",
        ResendVerificationEmailView.as_view(),
        name="verify_email_resend",
    ),
    path(
        "verify-email/<str:uidb64>/<str:token>/",
        VerifyEmailView.as_view(),
        name="verify_email",
    ),
    path(
        "verify-email/",
        VerifyEmailView.as_view(),
        name="verify_email_query",
    ),
]
