from django.apps import AppConfig


class EsignConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "esign"
    verbose_name = "E-sign (lease)"

    def ready(self):
        import esign.signals  # noqa: F401
