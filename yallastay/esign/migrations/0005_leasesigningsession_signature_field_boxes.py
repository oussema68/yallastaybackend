# Generated manually for signature_field_boxes JSONField.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("esign", "0004_renter_lister_signature_images"),
    ]

    operations = [
        migrations.AddField(
            model_name="leasesigningsession",
            name="signature_field_boxes",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Optional. Renter/lister signature rectangles on the contract PDF (points, PDF bottom-left origin): "
                    '{"renter": {"page_index": 0, "x": 72, "y": 72, "width": 200, "height": 48}, "lister": {...}}. '
                    "When set (both parties), signed PDFs overlay images on these boxes instead of appending certificate pages."
                ),
            ),
        ),
    ]
