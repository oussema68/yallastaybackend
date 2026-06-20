from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("lifestyle_services", "0006_partner_and_subscription_preferences"),
    ]

    operations = [
        migrations.CreateModel(
            name="LifestyleInterestFeedback",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("selected_services", models.JSONField(blank=True, default=list)),
                ("priority", models.CharField(blank=True, max_length=32)),
                ("other_detail", models.CharField(blank=True, max_length=500)),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="lifestyle_interest_feedback",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Lifestyle interest feedback",
                "verbose_name_plural": "Lifestyle interest feedback",
                "ordering": ["-created_at"],
            },
        ),
    ]
