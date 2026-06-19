from django.urls import path
from .views import (
    RoommateProfileView,
    RoommateSearchView,
    RoommateInterestView,
    RoommateInterestListView,
    RoommateInterestDetailView,
)

urlpatterns = [
    path("roommates/profile/", RoommateProfileView.as_view(), name="roommate-profile"),
    path("roommates/search/", RoommateSearchView.as_view(), name="roommate-search"),
    path(
        "roommates/interest/",
        RoommateInterestView.as_view(),
        name="roommate-interest-create",
    ),
    path(
        "roommates/interests/",
        RoommateInterestListView.as_view(),
        name="roommate-interest-list",
    ),
    path(
        "roommates/interests/<int:pk>/",
        RoommateInterestDetailView.as_view(),
        name="roommate-interest-detail",
    ),
]
