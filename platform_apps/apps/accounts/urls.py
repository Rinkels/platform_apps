# apps/accounts/urls.py
from django.urls import path
from .views import switch_context
from .api import api_context

urlpatterns = [
    path("switch/", switch_context, name="switch_context"),
    path("api/context/", api_context, name="api_context"),
]
