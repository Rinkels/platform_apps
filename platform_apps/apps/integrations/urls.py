# platform_apps/apps/integrations/urls.py
from django.urls import path
from .views_google_calendar import (
    google_calendar_connect,
    google_calendar_callback,
    google_calendar_disconnect,
)

urlpatterns = [
    path("google-calendar/connect/", google_calendar_connect, name="google_calendar_connect"),
    path("google-calendar/callback/", google_calendar_callback, name="google_calendar_callback"),
    path("google-calendar/disconnect/", google_calendar_disconnect, name="google_calendar_disconnect"),
]