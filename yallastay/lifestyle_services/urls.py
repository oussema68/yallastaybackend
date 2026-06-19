from django.urls import path

from .views import (
    LifestyleManagementOverviewView,
    LifestylePartnerListView,
    LifestylePlanListView,
    LifestyleSubscriptionListCreateView,
    LifestyleSubscriptionDetailView,
    LifestyleSubscriptionPreferencesView,
)

urlpatterns = [
    path(
        "lifestyle-partners/",
        LifestylePartnerListView.as_view(),
        name="lifestyle-partner-list",
    ),
    path(
        "lifestyle-plans/", LifestylePlanListView.as_view(), name="lifestyle-plan-list"
    ),
    path(
        "lifestyle-management/overview/",
        LifestyleManagementOverviewView.as_view(),
        name="lifestyle-management-overview",
    ),
    path(
        "lifestyle-subscriptions/",
        LifestyleSubscriptionListCreateView.as_view(),
        name="lifestyle-subscription-list-create",
    ),
    path(
        "lifestyle-subscriptions/<int:pk>/",
        LifestyleSubscriptionDetailView.as_view(),
        name="lifestyle-subscription-detail",
    ),
    path(
        "lifestyle-subscriptions/<int:pk>/preferences/",
        LifestyleSubscriptionPreferencesView.as_view(),
        name="lifestyle-subscription-preferences",
    ),
]
