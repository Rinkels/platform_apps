# platform_apps/apps/integrations/services/google_calendar.py
import json
from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ..models import GoogleCalendarCredential

def load_creds_for_user(user) -> Credentials:
    row = GoogleCalendarCredential.objects.get(user=user)
    info = json.loads(row.token_json)
    creds = Credentials.from_authorized_user_info(info, settings.GOOGLE_CALENDAR_SCOPES)

    # Refresh automatically if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        row.token_json = creds.to_json()
        row.save(update_fields=["token_json", "updated_at"])

    return creds

def calendar_service_for_user(user):
    creds = load_creds_for_user(user)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)