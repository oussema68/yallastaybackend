from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("listings", "0005_listing_assigned_realtor"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="owner_verification_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="listing",
            name="owner_verification_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Verified realtor who approved or rejected owner documents.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="owner_property_verifications_done",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="owner_verification_note",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="listing",
            name="owner_verification_status",
            field=models.CharField(
                choices=[
                    ("none", "Not requested"),
                    ("pending", "Pending realtor review"),
                    ("approved", "Approved by realtor"),
                    ("rejected", "Rejected by realtor"),
                ],
                db_index=True,
                default="none",
                max_length=20,
            ),
        ),
    ]
