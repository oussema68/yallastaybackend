from django.urls import path
from .verification_views import (
    UAEIDVerificationView,
    UniversityVerificationView,
    VerificationStatusView,
)

urlpatterns = [
    path("uae-id/", UAEIDVerificationView.as_view(), name="uae-id"),
    path("university/", UniversityVerificationView.as_view(), name="university"),
    path("status/", VerificationStatusView.as_view(), name="status"),
]
