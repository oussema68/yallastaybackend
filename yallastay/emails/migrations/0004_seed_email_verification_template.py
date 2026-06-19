from django.db import migrations


def seed_template(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.update_or_create(
        key="email_verification",
        defaults={
            "name": "Verify email address",
            "description": "Placeholders: {first_name}, {email}, {verification_link}",
            "subject": "Verify your Yallastay email",
            "body_text": (
                "Hi {first_name},\n\n"
                "Please confirm this email address by opening the link below:\n\n"
                "{verification_link}\n\n"
                "If you did not create an account, you can ignore this message.\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p>Please confirm your email address for your Yallastay account "
                "(<strong>{email}</strong>).</p>"
                '<p><a href="{verification_link}" '
                'style="display:inline-block;padding:12px 24px;background:#2563eb;'
                'color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">'
                "Verify email</a></p>"
                "<p>Or copy this link into your browser:<br/>"
                '<a href="{verification_link}">{verification_link}</a></p>'
                "<p>If you did not create an account, you can ignore this message.</p>"
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )


def unseed_template(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(key="email_verification").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0003_seed_email_templates"),
    ]

    operations = [
        migrations.RunPython(seed_template, unseed_template),
    ]
