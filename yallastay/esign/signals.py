"""Keep listing.leased in sync when a lease signing session completes (admin, webhooks, etc.)."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import LeaseSigningSession


@receiver(post_save, sender=LeaseSigningSession)
def sync_listing_leased_when_signing_completed(sender, instance, **kwargs):
    if instance.status != "completed":
        return
    listing = instance.reservation.listing
    if not listing.leased:
        listing.leased = True
        listing.save(update_fields=["leased", "updated_at"])
