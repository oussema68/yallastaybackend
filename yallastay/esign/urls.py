from django.urls import path

from .views import (
    LeaseSigningPdfView,
    LeaseSigningSessionContractPdfView,
    LeaseSigningSessionDetailView,
    LeaseSigningSessionListView,
    LeaseSigningSignView,
    LeaseSigningSignatureFieldsView,
    LeaseSigningUploadContractView,
)

urlpatterns = [
    path(
        "esign/sessions/", LeaseSigningSessionListView.as_view(), name="esign-sessions"
    ),
    path(
        "esign/sessions/<int:pk>/upload-contract/",
        LeaseSigningUploadContractView.as_view(),
        name="esign-upload-contract",
    ),
    path(
        "esign/sessions/<int:pk>/signature-fields/",
        LeaseSigningSignatureFieldsView.as_view(),
        name="esign-signature-fields",
    ),
    path(
        "esign/sessions/<int:pk>/contract-pdf/",
        LeaseSigningSessionContractPdfView.as_view(),
        name="esign-session-contract-pdf",
    ),
    path(
        "esign/sessions/<int:pk>/",
        LeaseSigningSessionDetailView.as_view(),
        name="esign-session-detail",
    ),
    path(
        "esign/sign/<str:token>/pdf/",
        LeaseSigningPdfView.as_view(),
        name="esign-sign-pdf",
    ),
    path(
        "esign/sign/<str:token>/",
        LeaseSigningSignView.as_view(),
        name="esign-sign",
    ),
]
