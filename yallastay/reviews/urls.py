from django.urls import path
from .views import ReviewListCreateView, ReviewDetailView, ReviewResponseCreateView

urlpatterns = [
    path("reviews/", ReviewListCreateView.as_view(), name="review-list-create"),
    path("reviews/<int:pk>/", ReviewDetailView.as_view(), name="review-detail"),
    path(
        "reviews/<int:pk>/response/",
        ReviewResponseCreateView.as_view(),
        name="review-response",
    ),
]
