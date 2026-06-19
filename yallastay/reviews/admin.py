from django.contrib import admin
from .models import Review, ReviewResponse


class ReviewResponseInline(admin.StackedInline):
    model = ReviewResponse
    extra = 0


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("reviewer", "reviewee", "listing", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("reviewer__email", "reviewee__email", "comment")
    inlines = [ReviewResponseInline]


@admin.register(ReviewResponse)
class ReviewResponseAdmin(admin.ModelAdmin):
    list_display = ("review", "created_at")
