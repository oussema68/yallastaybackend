from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_landlord_profile_approval"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="can_verify_documents",
            field=models.BooleanField(
                default=False,
                help_text="If true, user may use the verification staff API and console to review broker and owner documents.",
            ),
        ),
    ]
