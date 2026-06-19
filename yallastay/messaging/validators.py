from rest_framework import serializers

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
ALLOWED_ATTACHMENT_EXTENSIONS = frozenset(
    {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
)


def validate_message_attachment(file):
    if file is None:
        return file
    size = getattr(file, "size", 0) or 0
    if size > MAX_ATTACHMENT_BYTES:
        raise serializers.ValidationError("File must be 10 MB or smaller.")
    name = (getattr(file, "name", "") or "").lower()
    if not any(name.endswith(ext) for ext in ALLOWED_ATTACHMENT_EXTENSIONS):
        raise serializers.ValidationError(
            "Allowed file types: PDF, JPEG, PNG, WebP, HEIC."
        )
    return file
