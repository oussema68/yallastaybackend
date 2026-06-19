from django.urls import path
from .views import ReportCreateView, ReportListView, ReportDetailView

urlpatterns = [
    path("reports/", ReportListView.as_view(), name="report-list"),
    path("reports/submit/", ReportCreateView.as_view(), name="report-submit"),
    path("reports/<int:pk>/", ReportDetailView.as_view(), name="report-detail"),
]
