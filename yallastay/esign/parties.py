"""Who acts as the landlord-side party for lease signing (owner vs listing creator)."""

from __future__ import annotations

from listings.models import Listing


def lease_signing_lister_user(listing: Listing):
    """
    User who signs the lease on the landlord side and receives the lister magic link.

    When ``property_owner`` is set (e.g. realtor listed on behalf of the owner), the **owner**
    signs; otherwise the listing creator (``listed_by``) signs.
    """
    if listing.property_owner_id:
        return listing.property_owner
    return listing.listed_by
