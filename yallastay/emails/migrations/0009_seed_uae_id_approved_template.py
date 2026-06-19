from django.db import migrations


def seed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.update_or_create(
        key="uae_id_approved_user",
        defaults={
            "name": "UAE ID approved - user notification",
            "description": "Placeholders: {first_name}, {user_email}, {dashboard_url}",
            "subject": "Your Emirates ID verification is approved - Yallastay",
            "body_text": (
                "Hi {first_name},\n\n"
                "Good news - your Emirates ID verification has been approved. You can now use "
                "rental requests, viewings, messaging, and other features that require verified ID.\n\n"
                "Open your dashboard: {dashboard_url}\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p>Good news - your <strong>Emirates ID verification</strong> has been "
                "<strong>approved</strong>. You can now use rental requests, viewings, messaging, "
                "and other features that require verified ID.</p>"
                '<p><a href="{dashboard_url}">Go to your dashboard</a></p>'
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )


def unseed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(key="uae_id_approved_user").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0008_seed_uae_id_verification_templates"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
