from django.test import TestCase
from django.contrib.auth import get_user_model
from documents.models import Document

User = get_user_model()


class DocumentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com", password="Pass123!"
        )

    def test_document_str(self):
        doc = Document.objects.create(
            user=self.user,
            document_type="uae_id",
            file="documents/test.pdf",
        )
        self.assertIn(self.user.email, str(doc))
        self.assertIn("UAE ID", str(doc))
