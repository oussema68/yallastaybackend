"""Import files from ``MEDIA_ROOT`` into PostgreSQL ``StoredMedia`` rows."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import StoredMedia


class Command(BaseCommand):
    help = (
        "Copy files from the local MEDIA_ROOT tree into StoredMedia (PostgreSQL). "
        "Use once after enabling database media storage, or to backfill dev uploads before deploy."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be imported without writing.",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "USE_DATABASE_MEDIA", False):
            self.stderr.write(
                self.style.ERROR(
                    "USE_DATABASE_MEDIA is disabled (S3 active or USE_DATABASE_MEDIA=false)."
                )
            )
            return

        root = Path(settings.MEDIA_ROOT)
        if not root.is_dir():
            self.stdout.write(f"No directory at {root}; nothing to import.")
            return

        imported = 0
        skipped = 0
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if StoredMedia.objects.filter(name=rel).exists():
                skipped += 1
                continue
            data = path.read_bytes()
            content_type = mimetypes.guess_type(rel)[0] or ""
            if options["dry_run"]:
                self.stdout.write(f"would import {rel} ({len(data)} bytes)")
                imported += 1
                continue
            StoredMedia.objects.create(
                name=rel,
                content=data,
                content_type=content_type,
                size=len(data),
            )
            imported += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete: {imported} file(s) imported, {skipped} already in database."
            )
        )
