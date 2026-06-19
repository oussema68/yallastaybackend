from django.contrib import admin

from .models import (
    LifestylePartner,
    LifestylePlan,
    LifestylePlanBenefit,
    LifestylePlanSection,
    LifestyleService,
    LifestyleSubscription,
    LifestyleSubscriptionPreference,
)


class LifestyleServiceInline(admin.StackedInline):
    model = LifestyleService
    extra = 0


class LifestylePlanBenefitInline(admin.TabularInline):
    model = LifestylePlanBenefit
    extra = 0
    ordering = ("sort_order", "id")


@admin.register(LifestylePlanSection)
class LifestylePlanSectionAdmin(admin.ModelAdmin):
    list_display = ("plan", "title", "sort_order", "emoji")
    list_filter = ("plan",)
    ordering = ("plan", "sort_order", "id")
    inlines = [LifestylePlanBenefitInline]


class LifestylePlanSectionInline(admin.TabularInline):
    model = LifestylePlanSection
    extra = 0
    ordering = ("sort_order", "id")
    show_change_link = True


@admin.register(LifestylePlan)
class LifestylePlanAdmin(admin.ModelAdmin):
    list_display = ("name", "tier", "price", "currency", "is_active", "is_most_popular")
    list_filter = ("is_active", "is_most_popular")
    inlines = [LifestylePlanSectionInline, LifestyleServiceInline]


@admin.register(LifestyleService)
class LifestyleServiceAdmin(admin.ModelAdmin):
    list_display = ("plan", "service_type", "details")


@admin.register(LifestylePartner)
class LifestylePartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "partner_type", "area_label", "sort_order", "is_active")
    list_filter = ("partner_type", "is_active")


@admin.register(LifestyleSubscriptionPreference)
class LifestyleSubscriptionPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "subscription",
        "gym_partner",
        "cleaning_weekday",
        "cleaning_time_window",
    )
    raw_id_fields = ("subscription", "gym_partner")


@admin.register(LifestyleSubscription)
class LifestyleSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "reservation", "start_date", "end_date", "status")
