from django import template
from django.urls import NoReverseMatch, reverse

register = template.Library()


@register.simple_tag
def safe_url(route_name: str, fallback: str = "#"):
    try:
        return reverse(route_name)
    except NoReverseMatch:
        return fallback
