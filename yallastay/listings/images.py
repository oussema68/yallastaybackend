"""Create listing gallery rows with compressed main + thumbnail files."""

from __future__ import annotations

from core.image_processing import prepare_listing_image_upload

from .models import Listing, ListingImage


def create_listing_image(listing: Listing, uploaded_file, order: int) -> ListingImage:
    main, thumb = prepare_listing_image_upload(uploaded_file)
    return ListingImage.objects.create(
        listing=listing,
        image=main,
        thumbnail=thumb,
        order=order,
    )
