from django.contrib import admin
from .models import Area, University


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "country")
