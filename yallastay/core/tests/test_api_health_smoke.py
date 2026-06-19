"""Smoke checks suitable for uptime monitors (no auth)."""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class ApiRootHealthTests(TestCase):
    def test_root_returns_ok_json(self):
        c = APIClient()
        r = c.get("/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json().get("status"), "ok")
