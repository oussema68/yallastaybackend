from django.test import TestCase, Client


class ApiRootTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_api_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.json())
        self.assertEqual(response.json().get("status"), "ok")
