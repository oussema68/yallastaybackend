from django.db import migrations


def seed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.update_or_create(
        key="documents_received_user",
        defaults={
            "name": "Documents received - user acknowledgment",
            "description": (
                "Placeholders: {first_name}, {user_email}, {role_label}, "
                "{latest_document_label}, {present_list}, {missing_list}, "
                "{present_count}, {missing_count}"
            ),
            "subject": "We received your documents - Yallastay",
            "body_text": (
                "Hi {first_name},\n\n"
                "Thank you for uploading your documents. We have received them and "
                "our team will review them for verification.\n\n"
                "Latest upload: {latest_document_label}\n"
                "Account type: {role_label}\n\n"
                "We will notify you once verification is complete.\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p>Thank you for uploading your documents. We have received them and "
                "our team will review them for verification.</p>"
                "<p><strong>Latest upload:</strong> {latest_document_label}<br/>"
                "<strong>Account type:</strong> {role_label}</p>"
                "<p>We will notify you once verification is complete.</p>"
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )
    EmailTemplate.objects.update_or_create(
        key="documents_submitted_team",
        defaults={
            "name": "Documents submitted - verification team",
            "description": (
                "Placeholders: {first_name}, {user_email}, {role_label}, "
                "{latest_document_label}, {present_list}, {missing_list}, "
                "{present_count}, {missing_count}, {internal_note}"
            ),
            "subject": "[Yallastay] Documents uploaded - {user_email} ({role_label})",
            "body_text": (
                "Document upload notification\n\n"
                "User: {user_email}\n"
                "Name (first): {first_name}\n"
                "Profile role: {role_label}\n\n"
                "{internal_note}\n\n"
                "Present ({present_count}):\n{present_list}\n\n"
                "Missing ({missing_count}):\n{missing_list}\n\n"
                " -  Yallastay (automated)"
            ),
            "body_html": (
                "<p><strong>Document upload</strong></p>"
                "<p><strong>User:</strong> {user_email}<br/>"
                "<strong>Profile role:</strong> {role_label}</p>"
                "<p>{internal_note}</p>"
                "<p><strong>Present ({present_count})</strong></p>"
                '<pre style="white-space:pre-wrap;font-family:inherit;">'
                "{present_list}</pre>"
                "<p><strong>Missing ({missing_count})</strong></p>"
                '<pre style="white-space:pre-wrap;font-family:inherit;">'
                "{missing_list}</pre>"
                "<p> -  Yallastay (automated)</p>"
            ),
            "is_active": True,
        },
    )


def unseed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(
        key__in=("documents_received_user", "documents_submitted_team")
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0004_seed_email_verification_template"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
