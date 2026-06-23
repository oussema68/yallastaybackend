from collections import defaultdict
from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .permissions import IsRealtorOrLandlord, IsRealtor
from accounts.models import UserProfile, UniversityVerification
from listings.models import Favorite, Listing
from bookings.models import ViewingRequest, Reservation
from core.models import Area


class RenterDemographicsView(APIView):
    """
    GET: Aggregated tenant vs verified-student split, by university, by work area.
    Realtors only. Data anonymized.
    """

    permission_classes = [IsAuthenticated, IsRealtor]

    def get(self, request):
        profiles = UserProfile.objects.filter(role__in=["tenant", "student"])
        total = profiles.count()
        if total == 0:
            return Response(
                {
                    "tenants": 0,
                    "students": 0,
                    "tenants_pct": 0,
                    "students_pct": 0,
                    "by_university": [],
                    "by_work_area": [],
                }
            )

        tenants = profiles.filter(role="tenant").count()
        students = profiles.filter(role="student").count()
        tenants_pct = round(100 * tenants / total, 1)
        students_pct = round(100 * students / total, 1)

        # By university (from UniversityVerification - approved students)
        by_uni = list(
            UniversityVerification.objects.filter(status="approved")
            .values("university__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        by_university = [
            {"name": x["university__name"], "count": x["count"]} for x in by_uni
        ]

        # By work area (from UserProfile work_area - renters who set a work area)
        by_area = list(
            UserProfile.objects.filter(
                role__in=["tenant", "student"], work_area__isnull=False
            )
            .values("work_area__name", "work_area__slug")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        by_work_area = [
            {
                "name": x["work_area__name"],
                "slug": x["work_area__slug"],
                "count": x["count"],
            }
            for x in by_area
        ]

        return Response(
            {
                "tenants": tenants,
                "students": students,
                "tenants_pct": tenants_pct,
                "students_pct": students_pct,
                "total_renters": total,
                "by_university": by_university,
                "by_work_area": by_work_area,
            }
        )


class PopularAreasView(APIView):
    """
    GET: Areas with saves, viewings, reservations counts.
    Realtors only.
    """

    permission_classes = [IsAuthenticated, IsRealtor]

    def get(self, request):
        areas = list(Area.objects.values("id", "name", "slug").order_by("name"))
        saves_by_area = {
            row["listing__area_id"]: row["count"]
            for row in Favorite.objects.filter(listing__area__isnull=False)
            .values("listing__area_id")
            .annotate(count=Count("id"))
        }
        viewings_by_area = {
            row["listing__area_id"]: row["count"]
            for row in ViewingRequest.objects.filter(listing__area__isnull=False)
            .values("listing__area_id")
            .annotate(count=Count("id"))
        }
        reservations_by_area = {
            row["listing__area_id"]: row["count"]
            for row in Reservation.objects.filter(listing__area__isnull=False)
            .exclude(status="cancelled")
            .values("listing__area_id")
            .annotate(count=Count("id"))
        }

        result = []
        for area in areas:
            aid = area["id"]
            result.append(
                {
                    "id": aid,
                    "name": area["name"],
                    "slug": area["slug"],
                    "saves": saves_by_area.get(aid, 0),
                    "viewings": viewings_by_area.get(aid, 0),
                    "reservations": reservations_by_area.get(aid, 0),
                }
            )

        result.sort(
            key=lambda x: x["saves"] + x["viewings"] + x["reservations"],
            reverse=True,
        )
        return Response({"areas": result})


class MyListingsInsightsView(APIView):
    """
    GET: Realtor/landlord's own listings: saves, viewings, reservations by area and renter type.
    """

    permission_classes = [IsAuthenticated, IsRealtorOrLandlord]

    def get(self, request):
        user = request.user
        try:
            role = user.profile.role
        except Exception:
            role = None
        # Realtors: metrics for listings they own plus listings where a landlord assigned them (paperwork / marketing help).
        if role == "realtor":
            my_listings = Listing.objects.filter(
                Q(listed_by=user) | Q(assigned_realtor=user)
            )
        else:
            my_listings = Listing.objects.filter(listed_by=user)
        listing_ids = list(my_listings.values_list("id", flat=True))

        if not listing_ids:
            return Response(
                {
                    "total_listings": 0,
                    "total_saves": 0,
                    "total_viewings": 0,
                    "total_reservations": 0,
                    "by_area": [],
                    "by_renter_type": {"tenants": 0, "students": 0},
                }
            )

        total_saves = Favorite.objects.filter(listing_id__in=listing_ids).count()
        total_viewings = ViewingRequest.objects.filter(
            listing_id__in=listing_ids
        ).count()
        total_reservations = (
            Reservation.objects.filter(listing_id__in=listing_ids)
            .exclude(status="cancelled")
            .count()
        )

        # By area (aggregate from Favorite, ViewingRequest, Reservation via listing)
        fav_by_area = (
            Favorite.objects.filter(
                listing_id__in=listing_ids, listing__area__isnull=False
            )
            .values("listing__area__name", "listing__area__slug")
            .annotate(cnt=Count("id"))
        )
        view_by_area = (
            ViewingRequest.objects.filter(
                listing_id__in=listing_ids, listing__area__isnull=False
            )
            .values("listing__area__name", "listing__area__slug")
            .annotate(cnt=Count("id"))
        )
        res_by_area = (
            Reservation.objects.filter(
                listing_id__in=listing_ids, listing__area__isnull=False
            )
            .exclude(status="cancelled")
            .values("listing__area__name", "listing__area__slug")
            .annotate(cnt=Count("id"))
        )

        area_agg = defaultdict(
            lambda: {"saves": 0, "viewings": 0, "reservations": 0, "slug": ""}
        )
        for row in fav_by_area:
            name = row["listing__area__name"]
            area_agg[name]["slug"] = row["listing__area__slug"]
            area_agg[name]["saves"] += row["cnt"]
        for row in view_by_area:
            name = row["listing__area__name"]
            area_agg[name]["slug"] = row["listing__area__slug"]
            area_agg[name]["viewings"] += row["cnt"]
        for row in res_by_area:
            name = row["listing__area__name"]
            area_agg[name]["slug"] = row["listing__area__slug"]
            area_agg[name]["reservations"] += row["cnt"]

        # Add areas with listings but no activity
        for listing in my_listings.select_related("area"):
            if listing.area and listing.area.name not in area_agg:
                area_agg[listing.area.name] = {
                    "saves": 0,
                    "viewings": 0,
                    "reservations": 0,
                    "slug": listing.area.slug,
                }

        by_area = [
            {
                "name": k,
                "slug": v["slug"],
                "saves": v["saves"],
                "viewings": v["viewings"],
                "reservations": v["reservations"],
            }
            for k, v in sorted(
                area_agg.items(),
                key=lambda x: x[1]["saves"] + x[1]["viewings"] + x[1]["reservations"],
                reverse=True,
            )
        ]

        # By renter type (from users who favorited, requested viewing, or reserved)
        fav_users = set(
            Favorite.objects.filter(listing_id__in=listing_ids).values_list(
                "user_id", flat=True
            )
        )
        view_users = set(
            ViewingRequest.objects.filter(listing_id__in=listing_ids).values_list(
                "user_id", flat=True
            )
        )
        res_users = set(
            Reservation.objects.filter(listing_id__in=listing_ids).values_list(
                "user_id", flat=True
            )
        )
        user_ids = fav_users | view_users | res_users

        role_counts = (
            UserProfile.objects.filter(
                user_id__in=user_ids, role__in=["tenant", "student"]
            )
            .values("role")
            .annotate(cnt=Count("id"))
        )
        by_renter = {"tenants": 0, "students": 0}
        for r in role_counts:
            key = "tenants" if r["role"] == "tenant" else "students"
            by_renter[key] = r["cnt"]

        return Response(
            {
                "total_listings": len(listing_ids),
                "total_saves": total_saves,
                "total_viewings": total_viewings,
                "total_reservations": total_reservations,
                "by_area": by_area,
                "by_renter_type": by_renter,
            }
        )
