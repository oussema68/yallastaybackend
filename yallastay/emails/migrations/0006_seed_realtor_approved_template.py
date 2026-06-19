from django.db import migrations


def seed_template(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.update_or_create(
        key="realtor_approved_user",
        defaults={
            "name": "Realtor account approved",
            "description": "Placeholders: {first_name}, {agency_name}, {dashboard_url}",
            "subject": "Your broker account is approved - Yallastay",
            "body_text": (
                "Hi {first_name},\n\n"
                "Great news: your Yallastay brokerage account ({agency_name}) has been approved. "
                "You can now publish listings in line with Dubai DLD / RERA rules (including Trakheesi permits per listing).\n\n"
                "Open your dashboard:\n{dashboard_url}\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p>Great news: your Yallastay brokerage account "
                "(<strong>{agency_name}</strong>) has been approved. "
                "You can now publish listings in line with Dubai DLD / RERA rules "
                "(including Trakheesi permits per listing).</p>"
                '<p><a href="{dashboard_url}" '
                'style="display:inline-block;padding:12px 24px;background:#0d9488;'
                'color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">'
                "Open realtor dashboard</a></p>"
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )


def unseed_template(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(key="realtor_approved_user").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0005_seed_document_upload_templates"),
    ]

    operations = [
        migrations.RunPython(seed_template, unseed_template),
    ]
