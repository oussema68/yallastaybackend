from django.test import TestCase
from core.models import Area, University


class AreaModelTests(TestCase):
    def test_create_area(self):
        area = Area.objects.create(name="Dubai Marina", slug="dubai-marina")
        self.assertEqual(area.name, "Dubai Marina")
        self.assertEqual(area.slug, "dubai-marina")
        self.assertEqual(str(area), "Dubai Marina")

    def test_area_ordering(self):
        Area.objects.create(name="B", slug="b")
        Area.objects.create(name="A", slug="a")
        names = list(Area.objects.values_list("name", flat=True))
        self.assertEqual(names, ["A", "B"])


class UniversityModelTests(TestCase):
    def test_create_university(self):
        uni = University.objects.create(name="UAE University", domain="uaeu.ac.ae")
        self.assertEqual(uni.name, "UAE University")
        self.assertEqual(uni.domain, "uaeu.ac.ae")
        self.assertEqual(str(uni), "UAE University")

    def test_university_default_country(self):
        uni = University.objects.create(name="Test Uni", domain="test.ac.ae")
        self.assertEqual(uni.country, "UAE")
