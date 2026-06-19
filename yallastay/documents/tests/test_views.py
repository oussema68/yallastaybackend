from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import LandlordProfile, UserProfile, RealtorProfile
from core.models import Area
from documents.models import Document
from emails.models import EmailMessage
from listings.models import Listing

User = get_user_model()


class DocumentViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", password="Pass123!"
        )

    def test_list_documents_requires_auth(self):
        response = self.client.get("/api/documents/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_documents_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/documents/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_upload_document(self):
        self.client.force_authenticate(user=self.user)
        file = SimpleUploadedFile(
            "id.pdf", b"pdf content", content_type="application/pdf"
        )
        before = EmailMessage.objects.count()
        response = self.client.post(
            "/api/documents/",
            {
                "document_type": "uae_id",
                "file": file,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["document_type"], "uae_id")
        self.assertTrue(
            Document.objects.filter(user=self.user, document_type="uae_id").exists()
        )
        self.assertEqual(EmailMessage.objects.count() - before, 0)

    @override_settings(
        VERIFICATION_TEAM_EMAIL="verify@team.example.com",
        DEFAULT_FROM_EMAIL="noreply@example.com",
    )
    def test_batch_upload_queues_user_and_team_emails_once(self):
        UserProfile.objects.create(user=self.user, role="tenant")
        self.client.force_authenticate(user=self.user)
        f1 = SimpleUploadedFile(
            "id.pdf", b"pdf content", content_type="application/pdf"
        )
        f2 = SimpleUploadedFile("p.pdf", b"more", content_type="application/pdf")
        before = EmailMessage.objects.count()
        response = self.client.post(
            "/api/documents/batch/",
            {
                "document_type": ["passport", "residence_visa"],
                "file": [f1, f2],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(EmailMessage.objects.count() - before, 2)
        self.assertTrue(
            EmailMessage.objects.filter(
                template_key="documents_received_user", to_email=self.user.email
            ).exists()
        )
        team = EmailMessage.objects.get(template_key="documents_submitted_team")
        self.assertEqual(team.to_email, "verify@team.example.com")
        self.assertIn("tenant", team.body_text.lower())
        self.assertIn("2 file", team.body_text.lower())

    @override_settings(
        VERIFICATION_TEAM_EMAIL="", DEFAULT_FROM_EMAIL="noreply@example.com"
    )
    def test_batch_upload_queues_only_user_email_when_team_not_configured(self):
        self.client.force_authenticate(user=self.user)
        f1 = SimpleUploadedFile("id.pdf", b"x", content_type="application/pdf")
        before = EmailMessage.objects.count()
        response = self.client.post(
            "/api/documents/batch/",
            {"document_type": ["uae_id"], "file": [f1]},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EmailMessage.objects.count() - before, 1)
        self.assertTrue(
            EmailMessage.objects.filter(template_key="documents_received_user").exists()
        )
        self.assertFalse(
            EmailMessage.objects.filter(
                template_key="documents_submitted_team"
            ).exists()
        )

    def test_upload_document_invalid_type(self):
        self.client.force_authenticate(user=self.user)
        file = SimpleUploadedFile("id.pdf", b"content", content_type="application/pdf")
        response = self.client.post(
            "/api/documents/",
            {
                "document_type": "invalid_type",
                "file": file,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_own_document(self):
        doc = Document.objects.create(
            user=self.user,
            document_type="uae_id",
            file=SimpleUploadedFile("a.pdf", b"x", content_type="application/pdf"),
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/documents/{doc.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(pk=doc.pk).exists())

    def test_patch_replace_file(self):
        doc = Document.objects.create(
            user=self.user,
            document_type="uae_id",
            file=SimpleUploadedFile("old.pdf", b"old", content_type="application/pdf"),
        )
        self.client.force_authenticate(user=self.user)
        new_file = SimpleUploadedFile(
            "new.pdf", b"new bytes", content_type="application/pdf"
        )
        response = self.client.patch(
            f"/api/documents/{doc.id}/",
            {"file": new_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertIn(b"new bytes", doc.file.read())

    def test_retrieve_own_document(self):
        doc = Document.objects.create(
            user=self.user, document_type="uae_id", file="documents/test.pdf"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/documents/{doc.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_other_user_document_returns_404(self):
        doc = Document.objects.create(
            user=self.other_user, document_type="uae_id", file="documents/test.pdf"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/documents/{doc.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_document_content_type_without_object_id_returns_400(self):
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(Document)
        self.client.force_authenticate(user=self.user)
        file = SimpleUploadedFile("id.pdf", b"content", content_type="application/pdf")
        response = self.client.post(
            "/api/documents/",
            {
                "document_type": "uae_id",
                "file": file,
                "content_type_id": ct.id,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_realtor_license_rejected_for_non_realtor(self):
        UserProfile.objects.create(user=self.user, role="tenant")
        self.client.force_authenticate(user=self.user)
        file = SimpleUploadedFile("lic.pdf", b"pdf", content_type="application/pdf")
        response = self.client.post(
            "/api/documents/",
            {"document_type": "realtor_license", "file": file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_trade_license_rejected_for_non_realtor(self):
        UserProfile.objects.create(user=self.user, role="tenant")
        self.client.force_authenticate(user=self.user)
        file = SimpleUploadedFile("t.pdf", b"x", content_type="application/pdf")
        response = self.client.post(
            "/api/documents/",
            {"document_type": "trade_license", "file": file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_realtor_license_upload_syncs_to_realtor_profile(self):
        realtor_user = User.objects.create_user(
            email="realtor@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor_user, role="realtor")
        RealtorProfile.objects.create(user=realtor_user, agency_name="Test Agency")
        self.client.force_authenticate(user=realtor_user)
        file = SimpleUploadedFile(
            "rera.pdf", b"license bytes", content_type="application/pdf"
        )
        response = self.client.post(
            "/api/documents/",
            {"document_type": "realtor_license", "file": file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        realtor_user.realtor_profile.refresh_from_db()
        self.assertTrue(bool(realtor_user.realtor_profile.license_document))

    def test_title_deed_requires_pdf_extension(self):
        UserProfile.objects.create(user=self.user, role="landlord")
        LandlordProfile.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)
        file = SimpleUploadedFile(
            "deed.png", b"%PDF-1.4 fake", content_type="image/png"
        )
        response = self.client.post(
            "/api/documents/",
            {"document_type": "title_deed", "file": file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_title_deed_requires_pdf_magic_bytes(self):
        UserProfile.objects.create(user=self.user, role="landlord")
        LandlordProfile.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)
        file = SimpleUploadedFile(
            "deed.pdf", b"not-a-pdf-bytes", content_type="application/pdf"
        )
        response = self.client.post(
            "/api/documents/",
            {"document_type": "title_deed", "file": file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_title_deed_upload_valid_pdf(self):
        UserProfile.objects.create(user=self.user, role="landlord")
        LandlordProfile.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)
        file = SimpleUploadedFile(
            "deed.pdf", b"%PDF-1.4 test minimal content", content_type="application/pdf"
        )
        response = self.client.post(
            "/api/documents/",
            {"document_type": "title_deed", "file": file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["document_type"], "title_deed")

    def test_patch_title_deed_replace_must_be_valid_pdf(self):
        UserProfile.objects.create(user=self.user, role="landlord")
        LandlordProfile.objects.create(user=self.user)
        doc = Document.objects.create(
            user=self.user,
            document_type="title_deed",
            file=SimpleUploadedFile(
                "old.pdf", b"%PDF-1.4 old", content_type="application/pdf"
            ),
        )
        self.client.force_authenticate(user=self.user)
        bad = SimpleUploadedFile("new.pdf", b"XXXXX", content_type="application/pdf")
        response = self.client.patch(
            f"/api/documents/{doc.id}/",
            {"file": bad},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_assigned_realtor_can_retrieve_owner_title_deed_document(self):
        area = Area.objects.create(name="Marina Access", slug="marina-access")
        landlord = User.objects.create_user(
            email="ld-deed@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=landlord, role="landlord")
        LandlordProfile.objects.create(user=landlord)
        deed = Document.objects.create(
            user=landlord,
            document_type="title_deed",
            file=SimpleUploadedFile(
                "deed.pdf", b"%PDF-1.4 deed", content_type="application/pdf"
            ),
        )
        realtor = User.objects.create_user(
            email="ar-deed@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor, role="realtor")
        rp = RealtorProfile.objects.create(user=realtor, agency_name="Access Agency")
        rp.is_approved = True
        rp.save()
        Listing.objects.create(
            title="Unit",
            description="x",
            price=3000,
            type="studio",
            area=area,
            listed_by=landlord,
            assigned_realtor=realtor,
            title_deed_document=deed,
            trakheesi_permit_number="",
        )
        self.client.force_authenticate(user=realtor)
        response = self.client.get(f"/api/documents/{deed.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["document_type"], "title_deed")

    def test_assigned_realtor_can_retrieve_owner_uae_id_document(self):
        area = Area.objects.create(name="Marina ID", slug="marina-id")
        landlord = User.objects.create_user(
            email="ld-id@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=landlord, role="landlord")
        LandlordProfile.objects.create(user=landlord)
        id_doc = Document.objects.create(
            user=landlord,
            document_type="uae_id",
            file=SimpleUploadedFile(
                "emirates.pdf", b"%PDF-1.4 id", content_type="application/pdf"
            ),
        )
        realtor = User.objects.create_user(
            email="ar-id@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor, role="realtor")
        rp = RealtorProfile.objects.create(user=realtor, agency_name="ID Agency")
        rp.is_approved = True
        rp.save()
        Listing.objects.create(
            title="Unit B",
            description="x",
            price=3000,
            type="studio",
            area=area,
            listed_by=landlord,
            assigned_realtor=realtor,
            trakheesi_permit_number="",
        )
        self.client.force_authenticate(user=realtor)
        response = self.client.get(f"/api/documents/{id_doc.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["document_type"], "uae_id")

    def test_assigned_realtor_cannot_patch_owner_document(self):
        area = Area.objects.create(name="Marina Patch", slug="marina-patch")
        landlord = User.objects.create_user(
            email="ld-p@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=landlord, role="landlord")
        LandlordProfile.objects.create(user=landlord)
        deed = Document.objects.create(
            user=landlord,
            document_type="title_deed",
            file=SimpleUploadedFile(
                "d.pdf", b"%PDF-1.4", content_type="application/pdf"
            ),
        )
        realtor = User.objects.create_user(
            email="ar-p@example.com", password="Pass123!"
        )
        UserProfile.objects.create(user=realtor, role="realtor")
        rp = RealtorProfile.objects.create(user=realtor, agency_name="P")
        rp.is_approved = True
        rp.save()
        Listing.objects.create(
            title="U",
            description="x",
            price=3000,
            type="studio",
            area=area,
            listed_by=landlord,
            assigned_realtor=realtor,
            title_deed_document=deed,
            trakheesi_permit_number="",
        )
        self.client.force_authenticate(user=realtor)
        new_f = SimpleUploadedFile(
            "x.pdf", b"%PDF-1.4 new", content_type="application/pdf"
        )
        response = self.client.patch(
            f"/api/documents/{deed.id}/",
            {"file": new_f},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
