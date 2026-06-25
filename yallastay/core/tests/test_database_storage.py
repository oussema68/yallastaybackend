"""Tests for PostgreSQL-backed upload storage."""

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client, TestCase, override_settings

from core.models import StoredMedia
from core.storage.database import DatabaseStorage


@override_settings(
    USE_DATABASE_MEDIA=True,
    STORAGES={
        "default": {"BACKEND": "core.storage.database.DatabaseStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class DatabaseStorageTests(TestCase):
    def test_save_open_delete_round_trip(self):
        storage = DatabaseStorage()
        name = storage.save("listings/demo.png", ContentFile(b"fake-png-bytes"))
        self.assertTrue(storage.exists(name))
        self.assertEqual(storage.size(name), len(b"fake-png-bytes"))
        with storage.open(name) as handle:
            self.assertEqual(handle.read(), b"fake-png-bytes")
        storage.delete(name)
        self.assertFalse(storage.exists(name))

    def test_default_storage_uses_database(self):
        name = default_storage.save("listings/via-default.jpg", ContentFile(b"jpeg"))
        self.assertTrue(StoredMedia.objects.filter(name=name).exists())
        default_storage.delete(name)

    def test_serve_stored_media_url(self):
        StoredMedia.objects.create(
            name="listings/served.jpg",
            content=b"jpeg-bytes",
            content_type="image/jpeg",
            size=len(b"jpeg-bytes"),
        )
        client = Client()
        response = client.get("/media/listings/served.jpg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"jpeg-bytes")
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_serve_stored_media_missing_returns_404(self):
        client = Client()
        response = client.get("/media/listings/does-not-exist.jpg")
        self.assertEqual(response.status_code, 404)
