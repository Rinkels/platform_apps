from django.apps import AppConfig

class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "platform_apps.apps.common"
    label = "common"