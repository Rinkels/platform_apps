# platform_apps/apps/integrations/models.py  (or crm/models.py if you prefer)
from django.conf import settings
from django.db import models

class GoogleCalendarCredential(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="google_calendar_credential",
    )
    token_json = models.TextField()  # creds.to_json()
    scopes = models.TextField(default="")  # optional, for auditing/debug
    connected_email = models.EmailField(blank=True, default="")  # optional
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"GoogleCalendarCredential(user={self.user_id})"