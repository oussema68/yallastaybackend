from django.db import migrations


def seed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    seeds = [
        {
            "key": "welcome",
            "name": "Welcome",
            "description": "Placeholders: {first_name}, {email}",
            "subject": "Welcome to Yallastay",
            "body_text": (
                "Hi {first_name},\n\n"
                "Thanks for joining Yallastay - your account ({email}) is ready.\n\n"
                " -  The Yallastay team"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p>Thanks for joining Yallastay - your account ({email}) is ready.</p>"
                "<p> -  The Yallastay team</p>"
            ),
        },
        {
            "key": "verification_submitted",
            "name": "Verification submitted",
            "description": "Placeholders: {first_name}",
            "subject": "We received your verification",
            "body_text": (
                "Hi {first_name},\n\n"
                "We received your verification submission and will review it shortly.\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p>We received your verification submission and will review it shortly.</p>"
                "<p> -  Yallastay</p>"
            ),
        },
        {
            "key": "listing_update",
            "name": "Listing update",
            "description": "Placeholders: {first_name}, {listing_title}, {detail}",
            "subject": "Update: {listing_title}",
            "body_text": (
                "Hi {first_name},\n\n"
                'Regarding your listing "{listing_title}":\n{detail}\n\n'
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p>Regarding your listing <strong>{listing_title}</strong>:</p>"
                "<p>{detail}</p>"
                "<p> -  Yallastay</p>"
            ),
        },
    ]
    for row in seeds:
        key = row.pop("key")
        EmailTemplate.objects.update_or_create(
            key=key,
            defaults={**row, "is_active": True},
        )


def unseed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(
        key__in=["welcome", "verification_submitted", "listing_update"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0002_email_and_sms_templates"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
