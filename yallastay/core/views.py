from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets
from .models import Area, University
from .serializers import AreaSerializer, UniversitySerializer


@method_decorator(cache_page(60 * 15), name="list")
class AreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer


@method_decorator(cache_page(60 * 60), name="list")
class UniversityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = University.objects.all()
    serializer_class = UniversitySerializer
