"""Who is acting in a reservation context (renter vs lister)."""


def reservation_party(request, reservation):
    """Return ``'lister'``, ``'renter'``, or ``None``."""
    user = request.user
    try:
        role = user.profile.role
    except Exception:
        role = None
    if role in ("landlord", "realtor") and reservation.listing.listed_by_id == user.id:
        return "lister"
    if reservation.user_id == user.id:
        return "renter"
    return None
