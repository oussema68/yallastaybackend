# Generated manually - one stored PNG per signature placement (multi-box leases).

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("esign", "0005_leasesigningsession_signature_field_boxes"),
    ]

    operations = [
        migrations.AddField(
            model_name="leasesigningsession",
            name="renter_signature_slot_1",
            field=models.FileField(
                blank=True,
                max_length=500,
                upload_to="esign/signatures/%Y/%m/",
                help_text="Renter signature PNG for placement 1 of 3 (when multi-box).",
            ),
        ),
        migrations.AddField(
            model_name="leasesigningsession",
            name="renter_signature_slot_2",
            field=models.FileField(
                blank=True,
                max_length=500,
                upload_to="esign/signatures/%Y/%m/",
                help_text="Renter signature PNG for placement 2 of 3.",
            ),
        ),
        migrations.AddField(
            model_name="leasesigningsession",
            name="renter_signature_slot_3",
            field=models.FileField(
                blank=True,
                max_length=500,
                upload_to="esign/signatures/%Y/%m/",
                help_text="Renter signature PNG for placement 3 of 3.",
            ),
        ),
        migrations.AddField(
            model_name="leasesigningsession",
            name="lister_signature_slot_1",
            field=models.FileField(
                blank=True,
                max_length=500,
                upload_to="esign/signatures/%Y/%m/",
                help_text="Lister signature PNG for placement 1 of 3 (when multi-box).",
            ),
        ),
        migrations.AddField(
            model_name="leasesigningsession",
            name="lister_signature_slot_2",
            field=models.FileField(
                blank=True,
                max_length=500,
                upload_to="esign/signatures/%Y/%m/",
                help_text="Lister signature PNG for placement 2 of 3.",
            ),
        ),
        migrations.AddField(
            model_name="leasesigningsession",
            name="lister_signature_slot_3",
            field=models.FileField(
                blank=True,
                max_length=500,
                upload_to="esign/signatures/%Y/%m/",
                help_text="Lister signature PNG for placement 3 of 3.",
            ),
        ),
    ]
