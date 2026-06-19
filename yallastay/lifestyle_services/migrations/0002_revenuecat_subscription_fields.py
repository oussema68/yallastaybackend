# Generated manually for RevenueCat mobile subscription sync.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("lifestyle_services", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RevenueCatWebhookEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("event_id", models.CharField(max_length=255, unique=True)),
                ("event_type", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "RevenueCat webhook event",
                "verbose_name_plural": "RevenueCat webhook events",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="lifestylesubscription",
            name="billing_source",
            field=models.CharField(
                choices=[
                    ("internal", "Internal / API"),
                    ("stripe", "Stripe (web)"),
                    ("revenuecat", "RevenueCat (App Store / Play)"),
                ],
                default="internal",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="lifestylesubscription",
            name="revenuecat_environment",
            field=models.CharField(
                blank=True,
                help_text="SANDBOX or PRODUCTION from RevenueCat.",
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="lifestylesubscription",
            name="revenuecat_original_transaction_id",
            field=models.CharField(
                blank=True,
                help_text="Store original transaction id (Apple/Google) for webhook idempotency.",
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="lifestylesubscription",
            name="revenuecat_product_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="lifestylesubscription",
            name="revenuecat_store",
            field=models.CharField(
                blank=True,
                help_text="APP_STORE, PLAY_STORE, etc.",
                max_length=30,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="lifestylesubscription",
            name="reservation",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional when synced from mobile IAP before a booking is linked.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lifestyle_subscriptions",
                to="bookings.reservation",
            ),
        ),
    ]
