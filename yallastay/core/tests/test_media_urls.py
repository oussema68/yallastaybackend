"""absolute_media_url handles relative /media/ and absolute https (S3)."""

from django.test import RequestFactory, SimpleTestCase

from core.media_urls import absolute_media_url


class _FakeFieldFile:
    def __init__(self, url: str):
        self._url = url

    @property
    def url(self) -> str:
        return self._url


class AbsoluteMediaUrlTests(SimpleTestCase):
    def test_passes_through_https(self):
        f = _FakeFieldFile("https://bucket.s3.me-central-1.amazonaws.com/x?sig=1")
        self.assertEqual(absolute_media_url(None, f), f._url)

    def test_builds_absolute_from_relative(self):
        factory = RequestFactory()
        req = factory.get("/api/listings/")
        f = _FakeFieldFile("/media/listings/a.jpg")
        self.assertEqual(
            absolute_media_url(req, f),
            "http://testserver/media/listings/a.jpg",
        )
