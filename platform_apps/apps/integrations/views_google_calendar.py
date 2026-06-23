# platform_apps/apps/integrations/views_google_calendar.py
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from .models import GoogleCalendarCredential

def _redirect_uri(request) -> str:
    return request.build_absolute_uri(reverse("google_calendar_callback"))

@login_required
@require_http_methods(["GET"])
def google_calendar_connect(request):
    flow = Flow.from_client_secrets_file(
        str(settings.GOOGLE_CLIENT_SECRETS_FILE),
        scopes=settings.GOOGLE_CALENDAR_SCOPES,
        redirect_uri=_redirect_uri(request),
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # ensures refresh_token on first connect
    )

    request.session["google_calendar_oauth_state"] = state
    return redirect(auth_url)

@login_required
@require_http_methods(["GET"])
def google_calendar_callback(request):
    state = request.session.get("google_calendar_oauth_state")
    if not state:
        # user lost session or opened callback in a new browser
        return redirect("google_calendar_connect")

    flow = Flow.from_client_secrets_file(
        str(settings.GOOGLE_CLIENT_SECRETS_FILE),
        scopes=settings.GOOGLE_CALENDAR_SCOPES,
        state=state,
        redirect_uri=_redirect_uri(request),
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    creds = flow.credentials

    # Optional: fetch connected user email (nice for UI)
    connected_email = ""
    try:
        oauth2 = build("oauth2", "v2", credentials=creds, cache_discovery=False)
        me = oauth2.userinfo().get().execute()
        connected_email = (me or {}).get("email", "") or ""
    except Exception:
        pass

    GoogleCalendarCredential.objects.update_or_create(
        user=request.user,
        defaults={
            "token_json": creds.to_json(),
            "scopes": " ".join(settings.GOOGLE_CALENDAR_SCOPES),
            "connected_email": connected_email,
        },
    )

    # Send them back to wherever makes sense
    return redirect("crm:dashboard")  # change to your target

@login_required
@require_http_methods(["POST"])
def google_calendar_disconnect(request):
    GoogleCalendarCredential.objects.filter(user=request.user).delete()
    return redirect("crm:dashboard")