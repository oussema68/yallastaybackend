from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_trakheesi_and_realtor_orn"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_email_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="email_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
