from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "platform_apps.apps.accounts"   # <-- must match new module path
    label = "accounts"                      # <-- keep label stable (migrations)

    def ready(self):
        # Import for signal registration side effects.
        from . import signals  # noqa: F401