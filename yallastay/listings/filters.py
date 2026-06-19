from django_filters import rest_framework as filters
from .models import Listing


class ListingFilter(filters.FilterSet):
    area = filters.NumberFilter(field_name="area_id")
    area_slug = filters.CharFilter(field_name="area__slug", lookup_expr="icontains")
    type = filters.CharFilter(field_name="type")
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Listing
        fields = ["area", "area_slug", "type", "min_price", "max_price"]
