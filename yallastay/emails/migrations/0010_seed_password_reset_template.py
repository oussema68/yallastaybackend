from django.db import migrations


def seed_template(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.update_or_create(
        key="password_reset",
        defaults={
            "name": "Password reset",
            "description": "Placeholders: {first_name}, {email}, {reset_link}",
            "subject": "Reset your Yallastay password",
            "body_text": (
                "Hi {first_name},\n\n"
                "We received a request to reset the password for your Yallastay account "
                "({email}). Open the link below to choose a new password:\n\n"
                "{reset_link}\n\n"
                "If you did not request this, you can ignore this email.\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p>We received a request to reset the password for your Yallastay account "
                "(<strong>{email}</strong>).</p>"
                '<p><a href="{reset_link}" '
                'style="display:inline-block;padding:12px 24px;background:#2563eb;'
                'color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">'
                "Reset password</a></p>"
                "<p>Or copy this link into your browser:<br/>"
                '<a href="{reset_link}">{reset_link}</a></p>'
                "<p>If you did not request this, you can ignore this email.</p>"
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )


def unseed_template(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(key="password_reset").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0009_seed_uae_id_approved_template"),
    ]

    operations = [
        migrations.RunPython(seed_template, unseed_template),
    ]
