from django.urls import path
from .views import (
    DocumentListCreateView,
    DocumentBatchCreateView,
    DocumentDetailView,
)

app_name = "documents"
urlpatterns = [
    path("documents/", DocumentListCreateView.as_view(), name="document-list-create"),
    path(
        "documents/batch/",
        DocumentBatchCreateView.as_view(),
        name="document-batch-create",
    ),
    path("documents/<int:pk>/", DocumentDetailView.as_view(), name="document-detail"),
]
