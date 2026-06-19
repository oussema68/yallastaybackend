from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from accounts.permissions import IsUAEIDVerified
from .models import Review, ReviewResponse
from .serializers import (
    ReviewSerializer,
    ReviewCreateSerializer,
    ReviewResponseCreateSerializer,
)


class ReviewListCreateView(APIView):
    """
    GET: List reviews. Filter by ?user=<id> or ?listing=<id>.
    POST: Create review (requires UAE ID verification).
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsUAEIDVerified()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Review.objects.select_related(
            "reviewer", "reviewee", "listing"
        ).prefetch_related("response")
        user_id = self.request.query_params.get("user")
        listing_id = self.request.query_params.get("listing")
        if user_id:
            queryset = queryset.filter(reviewee_id=user_id)
        if listing_id:
            queryset = queryset.filter(listing_id=listing_id)
        return queryset

    def get(self, request):
        queryset = self.get_queryset()
        serializer = ReviewSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ReviewCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        reviewee = serializer.validated_data["reviewee_id"]
        listing = serializer.validated_data.get("listing_id")
        rating = serializer.validated_data["rating"]
        comment = serializer.validated_data.get("comment", "")

        review = Review.objects.create(
            reviewer=request.user,
            reviewee=reviewee,
            listing=listing,
            rating=rating,
            comment=comment,
        )
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ReviewDetailView(APIView):
    """GET: Single review. POST: Add response (reviewee only)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        return Response(ReviewSerializer(review).data)


class ReviewResponseCreateView(APIView):
    """POST: Landlord/realtor replies to a review. Only reviewee can respond."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        if review.reviewee != request.user:
            return Response(
                {"detail": "Only the reviewee can respond to this review."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if hasattr(review, "response"):
            return Response(
                {"detail": "A response already exists for this review."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ReviewResponseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ReviewResponse.objects.create(
            review=review,
            response_text=serializer.validated_data["response_text"],
        )
        review.refresh_from_db()
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
