from django.contrib import admin
from .models import Listing, ListingImage, Favorite


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "price",
        "type",
        "status",
        "leased",
        "owner_verification_status",
        "trakheesi_permit_number",
        "listed_by",
        "assigned_realtor",
        "area",
        "created_at",
    )
    list_filter = ("type", "status", "leased", "area", "owner_verification_status")
    search_fields = ("title", "description", "address", "trakheesi_permit_number")
    inlines = [ListingImageInline]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "listing", "created_at")
    list_filter = ("created_at",)
