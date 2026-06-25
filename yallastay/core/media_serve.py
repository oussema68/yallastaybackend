"""Serve uploads stored in PostgreSQL at ``MEDIA_URL`` paths."""

from __future__ import annotations

from django.http import Http404, HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def serve_stored_media(request, path: str):
    from core.models import StoredMedia

    key = path.lstrip("/")
    if not key:
        raise Http404("Media not found")
    try:
        obj = StoredMedia.objects.get(name=key)
    except StoredMedia.DoesNotExist as exc:
        raise Http404("Media not found") from exc

    content_type = obj.content_type or "application/octet-stream"
    response = HttpResponse(bytes(obj.content), content_type=content_type)
    response["Content-Length"] = obj.size
    response["Cache-Control"] = "public, max-age=86400"
    return response
