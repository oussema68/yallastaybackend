from django.urls import path
from .views import (
    ViewingRequestListCreateView,
    ViewingRequestDetailView,
    ReservationListCreateView,
    ReservationDetailView,
    ReservationMoveInView,
    RentFromAppView,
)

urlpatterns = [
    path(
        "viewings/", ViewingRequestListCreateView.as_view(), name="viewing-list-create"
    ),
    path(
        "viewings/<int:pk>/", ViewingRequestDetailView.as_view(), name="viewing-detail"
    ),
    path(
        "listings/<int:listing_id>/rent/",
        RentFromAppView.as_view(),
        name="listing-rent-from-app",
    ),
    path(
        "reservations/",
        ReservationListCreateView.as_view(),
        name="reservation-list-create",
    ),
    path(
        "reservations/<int:pk>/move-in/",
        ReservationMoveInView.as_view(),
        name="reservation-move-in",
    ),
    path(
        "reservations/<int:pk>/",
        ReservationDetailView.as_view(),
        name="reservation-detail",
    ),
]
