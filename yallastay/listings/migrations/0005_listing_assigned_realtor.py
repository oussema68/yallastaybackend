import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("listings", "0004_uae_verification_pipeline"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="assigned_realtor",
            field=models.ForeignKey(
                blank=True,
                help_text="Verified realtor chosen by the lister for this property.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_listings",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
