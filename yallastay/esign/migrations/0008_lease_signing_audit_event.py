# Generated manually for LeaseSigningAuditEvent (UAE e-sign audit trail).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("esign", "0007_alter_leasesigningsession_lister_signature_slot_1_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="LeaseSigningAuditEvent",
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
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            (
                                "sign_preview_accessed",
                                "Sign preview accessed",
                            ),
                            ("contract_pdf_viewed", "Contract PDF viewed"),
                            (
                                "electronic_consent_accepted",
                                "Electronic consent accepted",
                            ),
                            ("signature_committed", "Signature committed"),
                            (
                                "signing_session_completed",
                                "Signing session completed",
                            ),
                        ],
                        max_length=64,
                    ),
                ),
                ("actor_role", models.CharField(blank=True, max_length=20)),
                (
                    "ip_address",
                    models.GenericIPAddressField(blank=True, null=True),
                ),
                ("user_agent", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_events",
                        to="esign.leasesigningsession",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="leasesigningauditevent",
            index=models.Index(
                fields=["session", "-created_at"],
                name="esign_leases_session_0a8b2d_idx",
            ),
        ),
    ]
