from django.core.management.base import BaseCommand

from lifestyle_services.models import (
    LifestylePartner,
    LifestylePlan,
    LifestylePlanBenefit,
    LifestylePlanSection,
    LifestyleService,
)


class Command(BaseCommand):
    help = "Seed Essential, Comfort, Complete plans with sections/benefits and legacy service rows."

    def handle(self, *args, **options):
        plans_data = [
            {
                "name": "Essential",
                "tier": 1,
                "price": 300,
                "description": "Core bundle for renters who want essentials covered.",
                "tagline": "Young professionals & single expats",
                "is_most_popular": False,
                "sections": [
                    {
                        "title": "Wellness",
                        "emoji": "🏋️",
                        "items": [
                            "Gym membership (partner gym access)",
                            "Swimming pool access",
                        ],
                    },
                    {
                        "title": "Home Services",
                        "emoji": "🏠",
                        "items": [
                            "2× Home cleaning/month",
                            "1× Handyman visit/month",
                            "AC filter check (bi-annual)",
                            "Pest control (quarterly)",
                        ],
                    },
                    {
                        "title": "Mobility",
                        "emoji": "🚗",
                        "items": [
                            "1× Car wash at building/month",
                            "AED 75 Uber/Careem credits",
                        ],
                    },
                    {
                        "title": "Digital",
                        "emoji": "📱",
                        "items": [
                            "Streaming bundle (Netflix or Spotify)",
                            "App concierge chat support",
                        ],
                    },
                ],
                "legacy_services": [
                    ("cleaning", "2×/month + handyman + AC + pest (see sections)"),
                    ("internet", "Streaming + concierge chat"),
                    ("maintenance", "Handyman 1×/month"),
                    ("gym", "Partner gym + pool"),
                    ("support", "App concierge chat"),
                ],
            },
            {
                "name": "Comfort",
                "tier": 2,
                "price": 500,
                "description": "Everything in Essential, plus dining, entertainment & more.",
                "tagline": "Working couples & mid-income expats",
                "is_most_popular": True,
                "sections": [
                    {
                        "title": "Wellness",
                        "emoji": "🏋️",
                        "items": [
                            "Everything in Essential",
                            "1× On-demand massage/month",
                            "Yoga/Pilates studio access",
                            "Healthy juice/smoothie weekly delivery",
                        ],
                    },
                    {
                        "title": "Home Services",
                        "emoji": "🏠",
                        "items": [
                            "4× Home cleaning/month",
                            "Priority maintenance (next day)",
                            "1× Deep cleaning/month",
                        ],
                    },
                    {
                        "title": "Food & Dining",
                        "emoji": "🍽️",
                        "items": [
                            "AED 150 dining credits/month",
                            "Grocery delivery (5 orders free/month)",
                            "Weekly meal kit delivery",
                        ],
                    },
                    {
                        "title": "Entertainment",
                        "emoji": "🎭",
                        "items": [
                            "Cinema passes (2×/month: VOX or Reel)",
                            "Golf driving range credits (2×/month)",
                        ],
                    },
                    {
                        "title": "Mobility & Beauty",
                        "emoji": "🚗",
                        "items": [
                            "AED 150 Uber/Careem credits",
                            "Valet parking credits (4×/month)",
                            "1× Home salon/barber visit/month",
                        ],
                    },
                ],
                "legacy_services": [
                    ("cleaning", "4×/month + deep clean"),
                    ("internet", "Meal kit + grocery coordination"),
                    ("maintenance", "Priority next day"),
                    ("furniture", "Dining credits"),
                    ("gym", "Yoga/Pilates + massage"),
                    ("support", "Cinema + range credits"),
                ],
            },
            {
                "name": "Complete",
                "tier": 3,
                "price": 800,
                "description": "Full-service tier for families and premium renters.",
                "tagline": "Families, luxury renters & high earners",
                "is_most_popular": False,
                "sections": [
                    {
                        "title": "Wellness",
                        "emoji": "🏋️",
                        "items": [
                            "Everything in Comfort",
                            "1× Personal trainer session/month",
                            "Monthly spa day credit (partner hotels)",
                            "1× Nutritionist consultation/month",
                            "Mental wellness app (Headspace/Calm)",
                        ],
                    },
                    {
                        "title": "Home Services",
                        "emoji": "🏠",
                        "items": [
                            "Unlimited on-demand cleaning",
                            "Same-day priority maintenance",
                            "Personal concierge (dedicated WhatsApp agent)",
                            "Smart home device rental (1 device)",
                        ],
                    },
                    {
                        "title": "Food & Dining",
                        "emoji": "🍽️",
                        "items": [
                            "AED 250 dining credits/month",
                            "1× Personal chef session/month",
                            "Friday brunch credit (1×/month, partner hotels)",
                        ],
                    },
                    {
                        "title": "Entertainment & Experiences",
                        "emoji": "🎭",
                        "items": [
                            "Quarterly desert/yacht experience voucher",
                            "OSN+ streaming included",
                            "Kids activity credits: AED 150/month",
                        ],
                    },
                    {
                        "title": "Family",
                        "emoji": "👨‍👩‍👧",
                        "items": [
                            "Babysitting credits: 4hrs/month",
                            "1× Home tutoring session/month",
                            "Pet care included",
                        ],
                    },
                    {
                        "title": "Mobility & Beauty",
                        "emoji": "🚗",
                        "items": [
                            "AED 250 Uber/Careem credits",
                            "Chauffeur service (3hrs/month)",
                            "2× Car wash + 1× detailing/month",
                            "Unlimited valet parking credits",
                            "2× Home salon/barber/month",
                            "1× In-home massage upgrade (90 min)",
                        ],
                    },
                ],
                "legacy_services": [
                    ("cleaning", "Unlimited on-demand"),
                    ("internet", "OSN+ + chef + brunch"),
                    ("maintenance", "Same-day priority"),
                    ("furniture", "Smart device rental"),
                    ("gym", "Trainer + spa + nutrition"),
                    ("support", "Dedicated WhatsApp agent"),
                ],
            },
        ]

        for p in plans_data:
            plan, _ = LifestylePlan.objects.update_or_create(
                tier=p["tier"],
                defaults={
                    "name": p["name"],
                    "price": p["price"],
                    "description": p["description"],
                    "tagline": p.get("tagline", ""),
                    "is_most_popular": p.get("is_most_popular", False),
                    "is_active": True,
                },
            )
            self.stdout.write(f"Plan: {plan.name}")

            LifestylePlanSection.objects.filter(plan=plan).delete()
            for s_idx, section in enumerate(p.get("sections", [])):
                sec = LifestylePlanSection.objects.create(
                    plan=plan,
                    title=section["title"],
                    emoji=section.get("emoji", ""),
                    sort_order=s_idx,
                )
                for b_idx, text in enumerate(section.get("items", [])):
                    LifestylePlanBenefit.objects.create(
                        section=sec, text=text[:500], sort_order=b_idx
                    )
                self.stdout.write(
                    f"  Section: {section['title']} ({len(section.get('items', []))} items)"
                )

            for stype, details in p.get("legacy_services", []):
                LifestyleService.objects.update_or_create(
                    plan=plan,
                    service_type=stype,
                    defaults={"details": details},
                )

        gym_partners = [
            ("Fitness First", "Dubai Marina", 0),
            ("Gold's Gym", "JBR / Marina Walk", 1),
            ("TechnoGym Partner Hub", "Business Bay", 2),
            ("Warehouse Gym", "Al Quoz", 3),
        ]
        for name, area, order in gym_partners:
            LifestylePartner.objects.update_or_create(
                partner_type="gym",
                name=name,
                defaults={
                    "area_label": area,
                    "sort_order": order,
                    "is_active": True,
                },
            )
            self.stdout.write(f"  Partner (gym): {name}")

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded lifestyle plans (sections + legacy services) and partner gyms."
            )
        )
