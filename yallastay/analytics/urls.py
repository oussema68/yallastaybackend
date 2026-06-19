from django.urls import path
from .views import RenterDemographicsView, PopularAreasView, MyListingsInsightsView

urlpatterns = [
    path(
        "analytics/renter-demographics/",
        RenterDemographicsView.as_view(),
        name="renter-demographics",
    ),
    path("analytics/popular-areas/", PopularAreasView.as_view(), name="popular-areas"),
    path(
        "analytics/my-listings-insights/",
        MyListingsInsightsView.as_view(),
        name="my-listings-insights",
    ),
]
