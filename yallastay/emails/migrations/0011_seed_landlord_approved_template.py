from django.db import migrations


def seed_template(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.update_or_create(
        key="landlord_approved_user",
        defaults={
            "name": "Landlord account approved",
            "description": "Placeholders: {first_name}, {company_name}, {dashboard_url}",
            "subject": "Your owner account is approved - Yallastay",
            "body_text": (
                "Hi {first_name},\n\n"
                "Great news: your Yallastay landlord / owner account has been approved by our team.\n"
                "Company on file: {company_name}\n\n"
                "You can list properties and continue verification steps (Emirates ID, title deed) in the app.\n\n"
                "Open your dashboard:\n{dashboard_url}\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p>Great news: your Yallastay landlord / owner account has been approved by our team.</p>"
                "<p>Company on file: <strong>{company_name}</strong></p>"
                "<p>You can list properties and continue verification steps (Emirates ID, title deed) in the app.</p>"
                '<p><a href="{dashboard_url}" '
                'style="display:inline-block;padding:12px 24px;background:#0d9488;'
                'color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">'
                "Open dashboard</a></p>"
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )


def unseed_template(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(key="landlord_approved_user").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0010_seed_password_reset_template"),
    ]

    operations = [
        migrations.RunPython(seed_template, unseed_template),
    ]
