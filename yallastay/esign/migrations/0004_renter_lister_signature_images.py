from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("esign", "0003_lister_contract_pdf_upload"),
    ]

    operations = [
        migrations.AddField(
            model_name="leasesigningsession",
            name="renter_signature_image",
            field=models.FileField(
                blank=True,
                help_text="PNG captured when the renter signs (embedded on certificate page).",
                max_length=500,
                upload_to="esign/signatures/%Y/%m/",
            ),
        ),
        migrations.AddField(
            model_name="leasesigningsession",
            name="lister_signature_image",
            field=models.FileField(
                blank=True,
                help_text="PNG captured when the landlord/realtor signs (embedded on certificate page).",
                max_length=500,
                upload_to="esign/signatures/%Y/%m/",
            ),
        ),
    ]
