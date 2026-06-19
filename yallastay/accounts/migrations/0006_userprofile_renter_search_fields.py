from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_userprofile_role_tenant"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="place_of_work_or_studies",
            field=models.CharField(
                blank=True,
                help_text="Employer, university, or school name (optional).",
                max_length=300,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="sex",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Not specified"),
                    ("female", "Female"),
                    ("male", "Male"),
                    ("prefer_not_to_say", "Prefer not to say"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="age",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Self-reported age for search filters (optional).",
                null=True,
            ),
        ),
    ]
