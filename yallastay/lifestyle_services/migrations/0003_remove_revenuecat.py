# Remove RevenueCat / mobile IAP webhook fields; restore reservation as required.

import django.db.models.deletion
from django.db import migrations, models


def delete_subscriptions_without_reservation(apps, schema_editor):
    LifestyleSubscription = apps.get_model(
        "lifestyle_services", "LifestyleSubscription"
    )
    LifestyleSubscription.objects.filter(reservation__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("lifestyle_services", "0002_revenuecat_subscription_fields"),
    ]

    operations = [
        migrations.RunPython(
            delete_subscriptions_without_reservation, migrations.RunPython.noop
        ),
        migrations.DeleteModel(name="RevenueCatWebhookEvent"),
        migrations.RemoveField(
            model_name="lifestylesubscription", name="billing_source"
        ),
        migrations.RemoveField(
            model_name="lifestylesubscription", name="revenuecat_environment"
        ),
        migrations.RemoveField(
            model_name="lifestylesubscription",
            name="revenuecat_original_transaction_id",
        ),
        migrations.RemoveField(
            model_name="lifestylesubscription", name="revenuecat_product_id"
        ),
        migrations.RemoveField(
            model_name="lifestylesubscription", name="revenuecat_store"
        ),
        migrations.AlterField(
            model_name="lifestylesubscription",
            name="reservation",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lifestyle_subscriptions",
                to="bookings.reservation",
            ),
        ),
    ]
