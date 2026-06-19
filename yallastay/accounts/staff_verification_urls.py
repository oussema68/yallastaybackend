from django.urls import path

from .staff_verification_views import (
    StaffLandlordDecisionView,
    StaffRealtorDecisionView,
    StaffVerificationQueueView,
)

urlpatterns = [
    path(
        "queue/", StaffVerificationQueueView.as_view(), name="staff-verification-queue"
    ),
    path(
        "realtors/<int:user_id>/decision/",
        StaffRealtorDecisionView.as_view(),
        name="staff-realtor-decision",
    ),
    path(
        "landlords/<int:user_id>/decision/",
        StaffLandlordDecisionView.as_view(),
        name="staff-landlord-decision",
    ),
]
