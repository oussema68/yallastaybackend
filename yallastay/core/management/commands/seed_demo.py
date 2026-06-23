"""Seed accounts, listings, and a reservation for live demos / presentations."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import (
    LandlordProfile,
    RealtorProfile,
    UAEIDVerification,
    UserProfile,
)
from bookings.models import Reservation
from core.models import Area
from listings.models import Listing
from messaging.models import Conversation, Message
from roommates.models import RoommateProfile

User = get_user_model()

DEMO_PASSWORD = "DemoPresent2026!"

LANDLORD_EMAIL = "demo.landlord@present.yallastay"
TENANT_EMAIL = "demo.tenant@present.yallastay"
TEAM_EMAIL = "demo.team@present.yallastay"
VERIFY_EMAIL = "demo.verify@present.yallastay"
REALTOR_EMAIL = "demo.realtor@present.yallastay"
REALTOR_PENDING_EMAIL = "demo.realtor-pending@present.yallastay"
OWNER_PENDING_EMAIL = "demo.owner-pending@present.yallastay"

LISTING_TITLE_PRIMARY = "[Demo] Marina · furnished 1BR"
LISTING_TITLE_SECONDARY = "[Demo] JLT · studio near metro"
LISTING_TITLE_REALTOR = "[Demo] Marina · broker-listed studio"


class Command(BaseCommand):
    help = (
        "Create demo landlord (staff-approved), tenant (UAE approved + roommate), lifestyle team, "
        "verification staff, approved + pending realtors, pending owner (staff queue), three "
        "listings, confirmed reservation, and a sample Messages thread. Requires seed_core areas. "
        f"Password for all demo accounts: {DEMO_PASSWORD}"
    )

    def handle(self, *args, **options):
        marina = Area.objects.filter(slug="dubai-marina").first()
        jlt = Area.objects.filter(slug="jlt").first()
        if not marina or not jlt:
            self.stderr.write(
                self.style.ERROR(
                    "Areas missing. Run: python manage.py seed_core\n"
                    "Then: python manage.py seed_lifestyle"
                )
            )
            return

        today = timezone.now().date()
        stay_start = today - timedelta(days=14)
        stay_end = today + timedelta(days=320)

        landlord = self._ensure_user(LANDLORD_EMAIL, role="landlord")
        LandlordProfile.objects.update_or_create(
            user=landlord,
            defaults={
                "is_approved": True,
                "approved_at": timezone.now(),
            },
        )

        tenant = self._ensure_user(TENANT_EMAIL, role="tenant")
        UserProfile.objects.filter(user=tenant).update(is_email_verified=True)
        UAEIDVerification.objects.update_or_create(
            user=tenant,
            defaults={
                "id_hash": "demo_present_sha256_placeholder_do_not_use_prod",
                "status": "approved",
                "verified_at": timezone.now(),
            },
        )

        demo_rp, _ = RoommateProfile.objects.update_or_create(
            user=tenant,
            defaults={
                "bio": "Demo tenant - open to shared Marina / JLT.",
                "budget_min": 2500,
                "budget_max": 6500,
                "move_in_date": today,
                "lifestyle_preferences": "Quiet, respectful flatmates.",
                "is_looking": True,
            },
        )
        demo_rp.preferred_areas.set([marina.pk, jlt.pk])

        team = self._ensure_user(TEAM_EMAIL, role="tenant")
        UserProfile.objects.filter(user=team).update(
            is_email_verified=True,
            can_manage_lifestyle=True,
        )

        verify = self._ensure_user(VERIFY_EMAIL, role="tenant")
        UserProfile.objects.filter(user=verify).update(
            is_email_verified=True,
            can_verify_documents=True,
        )

        realtor = self._ensure_user(REALTOR_EMAIL, role="realtor")
        RealtorProfile.objects.update_or_create(
            user=realtor,
            defaults={
                "agency_name": "[Demo] Marina Realty",
                "brokerage_type": "agency",
                "rera_number": "712345",
                "orn": "ORN-DEMO-001",
                "is_approved": True,
                "approved_at": timezone.now(),
            },
        )

        realtor_pending = self._ensure_user(REALTOR_PENDING_EMAIL, role="realtor")
        RealtorProfile.objects.update_or_create(
            user=realtor_pending,
            defaults={
                "agency_name": "[Demo] Pending private broker",
                "brokerage_type": "private",
                "rera_number": "",
                "orn": "",
                "is_approved": False,
                "approved_at": None,
            },
        )

        owner_pending = self._ensure_user(OWNER_PENDING_EMAIL, role="landlord")
        LandlordProfile.objects.update_or_create(
            user=owner_pending,
            defaults={
                "company_name": "[Demo] Pending owner LLC",
                "is_emirati": True,
                "is_approved": False,
                "approved_at": None,
            },
        )

        listing1, _ = Listing.objects.update_or_create(
            title=LISTING_TITLE_PRIMARY,
            listed_by=landlord,
            defaults={
                "description": "Demo listing for presentations: Dubai Marina walkable.",
                "price": 7200,
                "currency": "AED",
                "type": "apartment",
                "status": "active",
                "bedrooms": 1,
                "bathrooms": 1,
                "area": marina,
                "address": "Marina Walk (demo)",
                "leased": False,
            },
        )
        Listing.objects.update_or_create(
            title=LISTING_TITLE_SECONDARY,
            listed_by=landlord,
            defaults={
                "description": "Second demo unit: Jumeirah Lakes Towers.",
                "price": 4800,
                "currency": "AED",
                "type": "studio",
                "status": "active",
                "bedrooms": 1,
                "bathrooms": 1,
                "area": jlt,
                "address": "Cluster demo (demo)",
                "leased": False,
            },
        )
        Listing.objects.update_or_create(
            title=LISTING_TITLE_REALTOR,
            listed_by=realtor,
            defaults={
                "description": "Demo listing published by an approved broker (Trakheesi-style flows).",
                "price": 5500,
                "currency": "AED",
                "type": "studio",
                "status": "active",
                "bedrooms": 1,
                "bathrooms": 1,
                "area": marina,
                "address": "Marina (broker demo)",
                "trakheesi_permit_number": "0000000001",
                "leased": False,
            },
        )

        Reservation.objects.update_or_create(
            listing=listing1,
            user=tenant,
            defaults={
                "start_date": stay_start,
                "end_date": stay_end,
                "status": "confirmed",
                "deposit_amount": 3600,
                "currency": "AED",
                "notes": "Seeded reservation for lifestyle / dashboard demos.",
            },
        )

        conv = Conversation.objects.filter(listing=listing1).first()
        if conv is None:
            conv = Conversation.objects.create(listing=listing1)
        conv.participants.add(tenant, landlord)
        if not conv.messages.exists():
            Message.objects.create(
                conversation=conv,
                sender=landlord,
                content=(
                    "Thanks for your interest in the Marina demo unit - happy to arrange a viewing."
                ),
            )

        self.stdout.write(self.style.SUCCESS("Demo seed complete.\n"))
        self.stdout.write("Accounts (same password):\n")
        self.stdout.write(f"  Landlord (approved): {LANDLORD_EMAIL}\n")
        self.stdout.write(f"  Tenant (UAE approved): {TENANT_EMAIL}\n")
        self.stdout.write(
            f"  Lifestyle team dashboard: {TEAM_EMAIL} (can_manage_lifestyle)\n"
        )
        self.stdout.write(
            f"  Verification console: {VERIFY_EMAIL} (can_verify_documents)\n"
        )
        self.stdout.write(f"  Realtor (approved): {REALTOR_EMAIL}\n")
        self.stdout.write(f"  Realtor (pending queue): {REALTOR_PENDING_EMAIL}\n")
        self.stdout.write(f"  Owner (pending queue): {OWNER_PENDING_EMAIL}\n")
        self.stdout.write(f"  Password: {DEMO_PASSWORD}\n")

    def _ensure_user(self, email: str, role: str) -> User:
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"is_active": True},
        )
        user.set_password(DEMO_PASSWORD)
        user.is_active = True
        user.save()
        UserProfile.objects.update_or_create(
            user=user,
            defaults={"role": role},
        )
        return user
