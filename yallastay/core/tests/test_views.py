from rest_framework.test import APITestCase
from rest_framework import status
from core.models import Area, University


class AreaViewSetTests(APITestCase):
    def setUp(self):
        Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        Area.objects.create(name="JLT", slug="jlt")

    def test_list_areas_unauthenticated(self):
        response = self.client.get("/api/areas/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = (
            response.data.get("results", response.data)
            if isinstance(response.data, dict)
            else response.data
        )
        self.assertGreaterEqual(len(data), 2)

    def test_retrieve_area(self):
        response = self.client.get("/api/areas/1/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("name", response.data)
        self.assertIn("slug", response.data)


class UniversityViewSetTests(APITestCase):
    def setUp(self):
        University.objects.create(name="UAE University", domain="uaeu.ac.ae")

    def test_list_universities(self):
        response = self.client.get("/api/universities/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
