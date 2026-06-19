from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="reservation",
            name="notes",
            field=models.TextField(
                blank=True,
                help_text="Optional message from the renter to the lister.",
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="external_reference",
            field=models.CharField(
                blank=True,
                help_text="External contract or DLD reference when synced.",
                max_length=120,
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="dld_metadata",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Opaque payload for future DLD/DRD API sync (status, ids, etc.).",
            ),
        ),
    ]
