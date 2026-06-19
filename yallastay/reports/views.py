from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Report
from .serializers import ReportSerializer, ReportCreateSerializer


class ReportCreateView(APIView):
    """POST: Submit a report (listing or user)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        report = Report.objects.create(
            reporter=request.user,
            reported_listing=data.get("listing_id"),
            reported_user=data.get("user_id"),
            reason=data["reason"],
        )
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ReportListView(APIView):
    """GET: List reports. Authenticated users see their own; staff see all."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            reports = (
                Report.objects.all()
                .select_related("reporter", "reported_listing", "reported_user")
                .order_by("-created_at")
            )
        else:
            reports = (
                Report.objects.filter(reporter=request.user)
                .select_related("reported_listing", "reported_user")
                .order_by("-created_at")
            )
        return Response(ReportSerializer(reports, many=True).data)


class ReportDetailView(APIView):
    """
    GET: Report detail.
    PATCH: Update status and admin_notes (staff only). Moderation workflow.
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        report = get_object_or_404(Report, pk=pk)
        if not user.is_staff and report.reporter != user:
            return None
        return report

    def get(self, request, pk):
        report = self.get_object(pk, request.user)
        if not report:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ReportSerializer(report).data)

    def patch(self, request, pk):
        if not request.user.is_staff:
            return Response({"detail": "Admin only."}, status=status.HTTP_403_FORBIDDEN)
        report = get_object_or_404(Report, pk=pk)
        status_val = request.data.get("status")
        admin_notes = request.data.get("admin_notes")
        if status_val in ("pending", "reviewed", "resolved", "dismissed"):
            report.status = status_val
        if admin_notes is not None:
            report.admin_notes = admin_notes
        report.save()
        return Response(ReportSerializer(report).data)
