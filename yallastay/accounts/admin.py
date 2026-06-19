from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from .models import (
    User,
    UserProfile,
    LandlordProfile,
    RealtorProfile,
    UAEIDVerification,
    UniversityVerification,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "first_name", "last_name", "is_staff")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email",)
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = ((None, {"fields": ("email", "password1", "password2")}),)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "phone",
        "is_email_verified",
        "can_manage_lifestyle",
        "can_verify_documents",
    )
    list_filter = (
        "role",
        "is_email_verified",
        "can_manage_lifestyle",
        "can_verify_documents",
    )


@admin.register(LandlordProfile)
class LandlordProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "company_name",
        "is_emirati",
        "needs_assisted_listing",
        "is_approved",
        "approved_at",
    )
    list_filter = ("is_approved", "needs_assisted_listing")
    actions = ["approve_landlords"]

    @admin.action(description="Approve selected landlords")
    def approve_landlords(self, request, queryset):
        n = 0
        now = timezone.now()
        for lp in queryset.filter(is_approved=False):
            lp.is_approved = True
            lp.approved_at = now
            lp.save()
            n += 1
        self.message_user(request, f"{n} landlord(s) approved.")


@admin.register(RealtorProfile)
class RealtorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "agency_name",
        "brokerage_type",
        "rera_number",
        "is_approved",
        "approved_at",
    )
    list_filter = ("is_approved", "brokerage_type")
    actions = ["approve_realtors"]

    @admin.action(description="Approve selected realtors")
    def approve_realtors(self, request, queryset):
        # Per-row save so post_save signals run (approval notification email).
        n = 0
        now = timezone.now()
        for rp in queryset.filter(is_approved=False):
            rp.is_approved = True
            rp.approved_at = now
            rp.save()
            n += 1
        self.message_user(request, f"{n} realtor(s) approved.")


@admin.register(UAEIDVerification)
class UAEIDVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "verified_at", "created_at")
    list_filter = ("status",)
    actions = ["approve_verifications", "reject_verifications"]

    @admin.action(description="Approve selected")
    def approve_verifications(self, request, queryset):
        # Per-row save so post_save signals run (approval notification email).
        now = timezone.now()
        n = 0
        for v in queryset.exclude(status="approved"):
            v.status = "approved"
            v.verified_at = now
            v.save()
            n += 1
        self.message_user(request, f"{n} UAE ID verification(s) approved.")

    @admin.action(description="Reject selected")
    def reject_verifications(self, request, queryset):
        updated = queryset.update(status="rejected", verified_at=None)
        self.message_user(request, f"{updated} UAE ID verification(s) rejected.")


@admin.register(UniversityVerification)
class UniversityVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "email",
        "university",
        "status",
        "verified_at",
        "created_at",
    )
    list_filter = ("status",)
    actions = ["approve_verifications", "reject_verifications"]

    @admin.action(description="Approve selected")
    def approve_verifications(self, request, queryset):
        # Per-row save so post_save signals run (student role + in-app notification).
        now = timezone.now()
        n = 0
        for v in queryset.exclude(status="approved"):
            v.status = "approved"
            v.verified_at = now
            v.save()
            UserProfile.objects.filter(user=v.user).update(role="student")
            n += 1
        self.message_user(request, f"{n} university verification(s) approved.")

    @admin.action(description="Reject selected")
    def reject_verifications(self, request, queryset):
        n = 0
        for v in queryset.exclude(status="rejected"):
            v.status = "rejected"
            v.verified_at = None
            v.save()
            UserProfile.objects.filter(user=v.user).update(role="tenant")
            n += 1
        self.message_user(request, f"{n} university verification(s) rejected.")
