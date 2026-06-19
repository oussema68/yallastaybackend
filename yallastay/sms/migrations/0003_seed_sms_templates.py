from django.db import migrations


def seed_templates(apps, schema_editor):
    SmsTemplate = apps.get_model("sms", "SmsTemplate")
    seeds = [
        {
            "key": "otp_verification",
            "name": "OTP / verification code",
            "description": "Placeholders: {code}",
            "body": "Yallastay: your verification code is {code}. Do not share it with anyone.",
        },
        {
            "key": "viewing_reminder",
            "name": "Viewing reminder",
            "description": "Placeholders: {property_title}, {time}, {address}",
            "body": "Yallastay reminder: viewing for {property_title} at {time}. {address}",
        },
        {
            "key": "generic_message",
            "name": "Generic message",
            "description": "Placeholders: {message}",
            "body": "Yallastay: {message}",
        },
    ]
    for row in seeds:
        key = row.pop("key")
        SmsTemplate.objects.update_or_create(
            key=key,
            defaults={**row, "is_active": True},
        )


def unseed_templates(apps, schema_editor):
    SmsTemplate = apps.get_model("sms", "SmsTemplate")
    SmsTemplate.objects.filter(
        key__in=["otp_verification", "viewing_reminder", "generic_message"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("sms", "0002_email_and_sms_templates"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
