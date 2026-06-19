"""Model signals for accounts app."""

from __future__ import annotations

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .emails import (
    send_landlord_approved_email,
    send_realtor_approved_email,
    send_uae_id_approved_email,
)
from .models import (
    LandlordProfile,
    RealtorProfile,
    UAEIDVerification,
    UniversityVerification,
)


@receiver(pre_save, sender=RealtorProfile)
def _realtor_cache_approved_before(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = RealtorProfile.objects.get(pk=instance.pk)
            instance._was_approved_before = old.is_approved
        except RealtorProfile.DoesNotExist:
            instance._was_approved_before = False
    else:
        instance._was_approved_before = False


@receiver(post_save, sender=RealtorProfile)
def _realtor_notify_when_approved(sender, instance, created, **kwargs):
    if not instance.is_approved:
        return
    was = getattr(instance, "_was_approved_before", False)
    if was:
        return
    send_realtor_approved_email(instance.user, instance)


@receiver(pre_save, sender=LandlordProfile)
def _landlord_cache_approved_before(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = LandlordProfile.objects.get(pk=instance.pk)
            instance._was_approved_before = old.is_approved
        except LandlordProfile.DoesNotExist:
            instance._was_approved_before = False
    else:
        instance._was_approved_before = False


@receiver(post_save, sender=LandlordProfile)
def _landlord_notify_when_approved(sender, instance, created, **kwargs):
    if not instance.is_approved:
        return
    was = getattr(instance, "_was_approved_before", False)
    if was:
        return
    send_landlord_approved_email(instance.user, instance)
    from notifications.services import notify_user

    notify_user(
        instance.user,
        "general",
        "Landlord account approved",
        "Your owner account is verified. You can list properties and complete owner verification steps in the app.",
        link="/dashboard",
    )


@receiver(pre_save, sender=UAEIDVerification)
def _uae_cache_status_before(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = UAEIDVerification.objects.get(pk=instance.pk)
            instance._uae_status_before = old.status
        except UAEIDVerification.DoesNotExist:
            instance._uae_status_before = None
    else:
        instance._uae_status_before = None


@receiver(post_save, sender=UAEIDVerification)
def _uae_notify_when_approved(sender, instance, created, **kwargs):
    if instance.status != "approved":
        return
    before = getattr(instance, "_uae_status_before", None)
    if before == "approved":
        return
    send_uae_id_approved_email(instance.user)
    from notifications.services import notify_user

    notify_user(
        instance.user,
        "uae_verified",
        "Emirates ID approved",
        "You can message listers, book viewings, and send rental requests.",
        link="/dashboard",
    )


@receiver(pre_save, sender=UniversityVerification)
def _uni_cache_status_before(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = UniversityVerification.objects.get(pk=instance.pk)
            instance._uni_status_before = old.status
        except UniversityVerification.DoesNotExist:
            instance._uni_status_before = None
    else:
        instance._uni_status_before = None


@receiver(post_save, sender=UniversityVerification)
def _uni_notify_when_approved(sender, instance, created, **kwargs):
    if instance.status != "approved":
        return
    before = getattr(instance, "_uni_status_before", None)
    if before == "approved":
        return
    from notifications.services import notify_user

    notify_user(
        instance.user,
        "documents_verified",
        "University verification approved",
        "Your student email is verified. Student offers may apply when available.",
        link="/dashboard",
    )
