from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .emails import send_document_upload_emails
from .models import Document
from .access import user_can_read_document
from .serializers import (
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentFileUpdateSerializer,
)


def _sync_realtor_license(request, doc):
    if doc.document_type not in ("realtor_license", "rera_broker_card"):
        return
    from accounts.models import RealtorProfile

    try:
        rp = request.user.realtor_profile
    except RealtorProfile.DoesNotExist:
        return
    with doc.file.open("rb") as fh:
        name = doc.file.name.split("/")[-1] if doc.file.name else "license.pdf"
        rp.license_document.save(name, ContentFile(fh.read()), save=True)


class DocumentListCreateView(APIView):
    """
    GET: List current user's documents.
    POST: Upload a single document (no notification email - use batch for that).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        docs = Document.objects.filter(user=request.user).order_by("-created_at")
        return Response(DocumentSerializer(docs, many=True).data)

    def post(self, request):
        serializer = DocumentUploadSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ct_id = data.get("content_type_id")
        obj_id = data.get("object_id")
        content_type = None
        if ct_id is not None:
            from django.contrib.contenttypes.models import ContentType as CT

            content_type = get_object_or_404(CT, pk=ct_id)

        doc = Document.objects.create(
            user=request.user,
            document_type=data["document_type"],
            file=data["file"],
            content_type=content_type,
            object_id=obj_id,
        )

        _sync_realtor_license(request, doc)

        return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class DocumentBatchCreateView(APIView):
    """
    POST: Upload multiple files in one request; sends one user + one team email after all succeed.
    Multipart: repeat ``file`` and ``document_type`` in the same order (one type per file).
    """

    permission_classes = [IsAuthenticated]

    MAX_BATCH = 25

    def post(self, request):
        files = request.FILES.getlist("file")
        types = request.data.getlist("document_type")
        if len(files) != len(types):
            return Response(
                {
                    "detail": "Provide the same number of file and document_type fields, in matching order."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not files:
            return Response(
                {"detail": "No files provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(files) > self.MAX_BATCH:
            return Response(
                {"detail": f"At most {self.MAX_BATCH} files per request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created: list[Document] = []
        batch_keys: list[str] = []
        with transaction.atomic():
            for file_obj, doc_type in zip(files, types):
                ser = DocumentUploadSerializer(
                    data={"document_type": doc_type, "file": file_obj},
                    context={"request": request},
                )
                ser.is_valid(raise_exception=True)
                data = ser.validated_data
                doc = Document.objects.create(
                    user=request.user,
                    document_type=data["document_type"],
                    file=data["file"],
                    content_type=None,
                    object_id=None,
                )
                _sync_realtor_license(request, doc)
                created.append(doc)
                batch_keys.append(doc.document_type)

        last = created[-1]
        try:
            send_document_upload_emails(request.user, last, batch_type_keys=batch_keys)
        except Exception:
            pass

        return Response(
            DocumentSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(APIView):
    """GET: Retrieve. PATCH: Replace file. DELETE: Remove. Owner only."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        doc = get_object_or_404(Document, pk=pk)
        if not user_can_read_document(request.user, doc):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(DocumentSerializer(doc, context={"request": request}).data)

    def patch(self, request, pk):
        doc = get_object_or_404(Document, pk=pk, user=request.user)
        serializer = DocumentFileUpdateSerializer(doc, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        doc.refresh_from_db()
        _sync_realtor_license(request, doc)
        return Response(DocumentSerializer(doc).data)

    def delete(self, request, pk):
        doc = get_object_or_404(Document, pk=pk, user=request.user)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
