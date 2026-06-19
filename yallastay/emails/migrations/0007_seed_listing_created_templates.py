from django.db import migrations


def seed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.update_or_create(
        key="listing_created_first",
        defaults={
            "name": "First property listing published",
            "description": "Placeholders: {first_name}, {listing_title}, {listing_id}, {listing_url}",
            "subject": "Your first listing is live on Yallastay",
            "body_text": (
                "Hi {first_name},\n\n"
                "Congratulations - you’ve published your first property on Yallastay: "
                "“{listing_title}”.\n\n"
                "View your listing:\n{listing_url}\n\n"
                "Add photos and keep your Trakheesi permit details accurate to stay aligned "
                "with Dubai DLD / RERA.\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p><strong>Congratulations</strong> - you’ve published your "
                "<strong>first</strong> property on Yallastay: "
                "“{listing_title}”.</p>"
                '<p><a href="{listing_url}" '
                'style="display:inline-block;padding:12px 24px;background:#0d9488;'
                'color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">'
                "View listing</a></p>"
                "<p>Add photos and keep your Trakheesi permit details accurate to stay aligned "
                "with Dubai DLD / RERA.</p>"
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )
    EmailTemplate.objects.update_or_create(
        key="listing_created",
        defaults={
            "name": "Property listing published",
            "description": "Placeholders: {first_name}, {listing_title}, {listing_id}, {listing_url}",
            "subject": "New listing added - Yallastay",
            "body_text": (
                "Hi {first_name},\n\n"
                "Your property “{listing_title}” has been added to Yallastay.\n\n"
                "View or edit it here:\n{listing_url}\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p>Your property <strong>“{listing_title}”</strong> has been added to Yallastay.</p>"
                '<p><a href="{listing_url}" '
                'style="display:inline-block;padding:12px 24px;background:#0d9488;'
                'color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">'
                "View listing</a></p>"
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )


def unseed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(
        key__in=["listing_created_first", "listing_created"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0006_seed_realtor_approved_template"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
