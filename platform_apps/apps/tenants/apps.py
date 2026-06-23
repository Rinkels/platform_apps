from django.apps import AppConfig

class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "platform_apps.apps.tenants"
    label = "tenants"