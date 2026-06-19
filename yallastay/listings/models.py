from django.db import models
from django.conf import settings
from core.models import Area


class Listing(models.Model):
    TYPE_CHOICES = [
        ("room", "Single Room"),
        ("studio", "Studio"),
        ("apartment", "Apartment"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("paused", "Paused"),
        ("closed", "Closed"),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="AED")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    area_sqft = models.PositiveIntegerField(null=True, blank=True)
    address = models.CharField(max_length=300, blank=True)
    building = models.CharField(max_length=100, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    # Dubai DLD / RERA: Trakheesi permit is obtained by the broker via DLD Trakheesi; the
    # assigned realtor enters it on owner-listed properties. Realtor-listed ads set it at publish.
    trakheesi_permit_number = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="10-digit Trakheesi Advertising Permit (Dubai), entered by the advertising broker.",
    )
    leased = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True when a lease is fully signed for this listing - hidden from public search; still visible to lister and renter with a reservation.",
    )
    listed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings"
    )
    property_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_properties",
    )
    # Landlord self-listings only: owner-selected broker (see GET /api/auth/verified-realtors/).
    # Realtor-published listings use property_owner for the client, not assigned_realtor.
    assigned_realtor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_listings",
        help_text="Verified realtor chosen by the landlord when they list their own property.",
    )
    # Dubai / UAE: one advertised property per title deed; deed doc must match listing.
    title_deed_document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listings_by_title_deed",
        help_text="Ownership document for this unit; one listing per deed.",
    )
    title_deed_reference = models.CharField(
        max_length=300,
        blank=True,
        default="",
        help_text="Plot / unit / property reference as shown on the title deed (must match the upload).",
    )
    # After UAE ID + title deed on the listing, owner requests a verified realtor to confirm documents.
    owner_verification_status = models.CharField(
        max_length=20,
        choices=[
            ("none", "Not requested"),
            ("pending", "Pending realtor review"),
            ("approved", "Approved by realtor"),
            ("rejected", "Rejected by realtor"),
        ],
        default="none",
        db_index=True,
    )
    owner_verification_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owner_property_verifications_done",
        help_text="Verified realtor who approved or rejected owner documents.",
    )
    owner_verification_note = models.TextField(
        blank=True,
        default="",
        help_text="Reason when rejected; optional comment when approved.",
    )
    owner_verification_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["title_deed_document"],
                condition=models.Q(title_deed_document__isnull=False),
                name="unique_listing_per_title_deed_document",
            ),
        ]

    def __str__(self):
        return self.title


class ListingOwnerInvite(models.Model):
    """Realtor invites a landlord by email; accepting links ``property_owner`` on the listing."""

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="owner_invites",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_owner_invites_sent",
    )
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listing_owner_invites_accepted",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["listing", "email"]),
        ]

    def __str__(self):
        return f"Owner invite {self.email} → listing {self.listing_id}"


class ListingImage(models.Model):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="listings/")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.listing.title} - image {self.order}"


class Favorite(models.Model):
    """Interested list - available to all users including non-UAE ID."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "listing"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} favorited {self.listing.title}"
