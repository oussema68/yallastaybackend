from django.core.management.base import BaseCommand
from core.models import Area, University

AREAS = [
    ("Dubai Marina", "dubai-marina"),
    ("Academic City", "academic-city"),
    ("Knowledge Village", "knowledge-village"),
    ("JLT", "jlt"),
    ("Business Bay", "business-bay"),
    ("International City", "international-city"),
    ("Dubai Sports City", "dubai-sports-city"),
    ("Silicon Oasis", "silicon-oasis"),
]

UNIVERSITIES = [
    ("American University of Dubai", "aud.ac.ae"),
    ("American University in Dubai", "aud.edu"),
    ("Heriot-Watt University Dubai", "hw.ac.uk"),
    ("Middlesex University Dubai", "mdx.ac.ae"),
    ("University of Dubai", "ud.ac.ae"),
    ("University of Wollongong Dubai", "uowdubai.ac.ae"),
    ("Zayed University", "zu.ac.ae"),
    ("UAE University", "uaeu.ac.ae"),
    ("Khalifa University", "ku.ac.ae"),
]


class Command(BaseCommand):
    help = "Seed Area and University models with Dubai data"

    def handle(self, *args, **options):
        for name, slug in AREAS:
            Area.objects.get_or_create(slug=slug, defaults={"name": name})
            self.stdout.write(f"Area: {name}")

        for name, domain in UNIVERSITIES:
            University.objects.get_or_create(domain=domain, defaults={"name": name})
            self.stdout.write(f"University: {name}")

        self.stdout.write(self.style.SUCCESS("Seeded core data."))
