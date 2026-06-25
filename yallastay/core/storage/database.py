"""Store user uploads in PostgreSQL so they survive Railway redeploys (no S3/volume required)."""

from __future__ import annotations

import mimetypes

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.encoding import filepath_to_uri


class DatabaseStorage(Storage):
    """Django storage backend backed by ``core.models.StoredMedia``."""

    def __init__(self, media_url: str | None = None):
        self._media_url = media_url or settings.MEDIA_URL

    def _normalize_name(self, name: str) -> str:
        return name.replace("\\", "/").lstrip("/")

    def _open(self, name, mode="rb"):
        from core.models import StoredMedia

        name = self._normalize_name(name)
        try:
            obj = StoredMedia.objects.get(name=name)
        except StoredMedia.DoesNotExist as exc:
            raise FileNotFoundError(name) from exc
        return ContentFile(bytes(obj.content), name=name)

    def _save(self, name, content):
        from core.models import StoredMedia

        name = self._normalize_name(name)
        content.seek(0)
        data = content.read()
        content_type = getattr(content, "content_type", None) or mimetypes.guess_type(name)[0] or ""
        StoredMedia.objects.update_or_create(
            name=name,
            defaults={
                "content": data,
                "content_type": content_type,
                "size": len(data),
            },
        )
        return name

    def delete(self, name):
        from core.models import StoredMedia

        StoredMedia.objects.filter(name=self._normalize_name(name)).delete()

    def exists(self, name):
        from core.models import StoredMedia

        return StoredMedia.objects.filter(name=self._normalize_name(name)).exists()

    def size(self, name):
        from core.models import StoredMedia

        try:
            return StoredMedia.objects.get(name=self._normalize_name(name)).size
        except StoredMedia.DoesNotExist as exc:
            raise FileNotFoundError(name) from exc

    def url(self, name):
        name = self._normalize_name(name)
        return f"{self._media_url.rstrip('/')}/{filepath_to_uri(name)}"

    def get_modified_time(self, name):
        from core.models import StoredMedia

        try:
            return StoredMedia.objects.get(name=self._normalize_name(name)).updated_at
        except StoredMedia.DoesNotExist as exc:
            raise FileNotFoundError(name) from exc

    def get_created_time(self, name):
        from core.models import StoredMedia

        try:
            return StoredMedia.objects.get(name=self._normalize_name(name)).created_at
        except StoredMedia.DoesNotExist as exc:
            raise FileNotFoundError(name) from exc
