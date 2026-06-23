from django import template

from platform_apps.apps.common.services.menu_loader import load_menu, filter_menu_for_user

register = template.Library()


@register.inclusion_tag("common/_side_menu.html", takes_context=True)
def render_side_menu(context):
    request = context["request"]
    menu = load_menu()
    menu = filter_menu_for_user(menu, request.user)
    return {"menu": menu, "request": request}
