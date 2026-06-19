from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_alter_notification_notification_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="link",
            field=models.CharField(
                blank=True,
                help_text="Frontend path (e.g. /dashboard) or absolute URL.",
                max_length=500,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("booking", "Booking"),
                    ("viewing", "Viewing"),
                    ("message", "Message"),
                    ("payment", "Payment"),
                    ("lifestyle", "Lifestyle"),
                    ("review", "Review"),
                    ("listing", "Listing"),
                    ("general", "General"),
                    ("welcome", "Welcome"),
                    ("email_verified", "Email verified"),
                    ("documents_verified", "Documents verified"),
                    ("uae_verified", "UAE ID verified"),
                    ("acceptance", "Acceptance"),
                    ("contract", "Contract"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="notificationpreference",
            name="notification_type",
            field=models.CharField(default="general", max_length=30),
        ),
    ]
