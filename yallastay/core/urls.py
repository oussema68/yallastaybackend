from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AreaViewSet, UniversityViewSet

router = DefaultRouter()
router.register(r"areas", AreaViewSet, basename="area")
router.register(r"universities", UniversityViewSet, basename="university")

urlpatterns = [
    path("", include(router.urls)),
]
