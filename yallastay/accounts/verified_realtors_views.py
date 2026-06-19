"""Verified realtors for owner selection (private brokers sort before agency)."""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from documents.uae_pipeline import verified_realtors_queryset

from .serializers import VerifiedRealtorSerializer


class VerifiedRealtorsListView(generics.ListAPIView):
    """
    GET: Platform-approved realtors only.
    Ordering: private brokers first (less paperwork), then agency brokers, by agency name.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = VerifiedRealtorSerializer

    def get_queryset(self):
        return verified_realtors_queryset()
