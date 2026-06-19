from django.db import migrations


def seed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.update_or_create(
        key="uae_id_submitted_user",
        defaults={
            "name": "UAE ID submitted - user acknowledgment",
            "description": (
                "Placeholders: {first_name}, {user_email}, {verify_url}, {document_note}"
            ),
            "subject": "We received your Emirates ID verification - Yallastay",
            "body_text": (
                "Hi {first_name},\n\n"
                "Thank you - we have received your Emirates ID verification details. "
                "Your submission is pending review by our team.\n\n"
                "{document_note}\n\n"
                "We will email you again when your verification has been approved or if we need more information.\n\n"
                "You can check status anytime: {verify_url}\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p>Thank you - we have received your <strong>Emirates ID verification</strong> details. "
                "Your submission is <strong>pending review</strong> by our team.</p>"
                "<p>{document_note}</p>"
                "<p>We will email you again when your verification has been approved or if we need more information.</p>"
                '<p><a href="{verify_url}">Check verification status</a></p>'
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )
    EmailTemplate.objects.update_or_create(
        key="uae_id_submitted_team",
        defaults={
            "name": "UAE ID submitted - verification team",
            "description": (
                "Placeholders: {first_name}, {user_email}, {user_id}, {document_note}, "
                "{admin_uae_list_url}"
            ),
            "subject": "[Yallastay] Emirates ID submitted - {user_email} (user #{user_id})",
            "body_text": (
                "UAE ID verification submitted\n\n"
                "User ID: {user_id}\n"
                "Email: {user_email}\n"
                "First name: {first_name}\n\n"
                "{document_note}\n\n"
                "Review in Django admin: {admin_uae_list_url}\n\n"
                " -  Yallastay (automated)"
            ),
            "body_html": (
                "<p><strong>UAE ID verification submitted</strong></p>"
                "<p><strong>User ID:</strong> {user_id}<br/>"
                "<strong>Email:</strong> {user_email}<br/>"
                "<strong>First name:</strong> {first_name}</p>"
                "<p>{document_note}</p>"
                '<p><a href="{admin_uae_list_url}">Open UAE ID verifications in admin</a></p>'
                "<p> -  Yallastay (automated)</p>"
            ),
            "is_active": True,
        },
    )


def unseed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(
        key__in=("uae_id_submitted_user", "uae_id_submitted_team")
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0007_seed_listing_created_templates"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
