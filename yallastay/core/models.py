from django.db import models


class Area(models.Model):
    """Dubai areas for filters (e.g. Dubai Marina, JLT, Academic City)."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class University(models.Model):
    """Universities for student verification (e.g. @uaeu.ac.ae)."""

    name = models.CharField(max_length=200)
    domain = models.CharField(max_length=100, help_text="Email domain, e.g. uaeu.ac.ae")
    country = models.CharField(max_length=50, default="UAE")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Universities"

    def __str__(self):
        return self.name


class StoredMedia(models.Model):
    """
    Binary blob storage for user uploads when S3 is not configured.

    Listing photos, documents, e-sign PDFs, etc. are stored here on Railway/demo
    so they deploy with Postgres and survive container redeploys.
    """

    name = models.CharField(max_length=500, unique=True, db_index=True)
    content = models.BinaryField()
    content_type = models.CharField(max_length=127, blank=True, default="")
    size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
