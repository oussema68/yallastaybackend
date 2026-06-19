"""Upload validation helpers for document types."""

from rest_framework import serializers


def validate_title_deed_pdf(uploaded_file) -> None:
    """Title deeds must be real PDFs: .pdf name and %PDF magic bytes."""
    if uploaded_file is None:
        return
    name = (getattr(uploaded_file, "name", "") or "").strip().lower()
    if not name.endswith(".pdf"):
        raise serializers.ValidationError("Title deed must be a PDF file (.pdf).")
    try:
        uploaded_file.seek(0)
        head = uploaded_file.read(5)
    finally:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
    if not head.startswith(b"%PDF"):
        raise serializers.ValidationError("The file does not appear to be a valid PDF.")


def ensure_title_deed_document_is_pdf(document) -> None:
    """Validate stored file on a Document used as title deed (e.g. when linking to a listing)."""
    name = (document.file.name or "").lower()
    if not name.endswith(".pdf"):
        raise serializers.ValidationError(
            "Title deed must be a PDF. Upload a .pdf file under Documents, then link it again."
        )
    try:
        with document.file.open("rb") as fh:
            head = fh.read(5)
    except Exception:
        raise serializers.ValidationError(
            "Could not read the title deed file. Re-upload it as a PDF under Documents."
        )
    if not head.startswith(b"%PDF"):
        raise serializers.ValidationError(
            "Title deed must be a valid PDF. Re-upload under Documents."
        )
