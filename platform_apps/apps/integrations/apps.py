from django.apps import AppConfig

class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "platform_apps.apps.integrations"
    label = "integrations"  # optional but nice and explicit