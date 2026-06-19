from django.db import migrations, models


def forwards_worker_to_tenant(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    UserProfile.objects.filter(role="worker").update(role="tenant")


def backwards_tenant_to_worker(apps, schema_editor):
    # Cannot map tenant → worker without losing data; forwards is one-way for role values.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_userprofile_email_verification"),
    ]

    operations = [
        migrations.RunPython(forwards_worker_to_tenant, backwards_tenant_to_worker),
        migrations.AlterField(
            model_name="userprofile",
            name="role",
            field=models.CharField(
                choices=[
                    ("tenant", "Tenant"),
                    ("student", "Student"),
                    ("landlord", "Landlord"),
                    ("realtor", "Realtor"),
                ],
                default="tenant",
                max_length=20,
            ),
        ),
    ]
