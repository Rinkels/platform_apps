import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings


MENU_REL_PATH = Path("dealermaster/config/menu/menu.json")


def _menu_path() -> Path:
    # settings.BASE_DIR points to the "dealermaster" folder in your repo layout
    return Path(settings.BASE_DIR) / MENU_REL_PATH


@lru_cache(maxsize=1)
def load_menu() -> Dict[str, Any]:
    """
    Loads menu.json once per process (cached). Restart server to reload.
    """
    p = _menu_path()
    data = json.loads(p.read_text(encoding="utf-8"))
    return data


def _has_permission(user, perm: Optional[str]) -> bool:
    """
    If no permission specified, treat as visible (group nodes often have no permission).
    If permission exists, use Django auth permissions.
    """
    if not perm:
        return True
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.has_perm(perm)


def filter_menu_for_user(menu: Dict[str, Any], user) -> Dict[str, Any]:
    """
    Returns a copy of menu with nodes removed if user lacks permission.
    Keeps group nodes if they still have visible children.
    """
    def filter_node(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        children = node.get("children") or []
        filtered_children: List[Dict[str, Any]] = []
        for c in children:
            fc = filter_node(c)
            if fc:
                filtered_children.append(fc)

        perm = node.get("permission")
        node_visible = _has_permission(user, perm)

        # If leaf node: must pass permission check
        if not filtered_children and not node_visible:
            return None

        # If group node with children: show if any child visible
        if filtered_children:
            new_node = dict(node)
            new_node["children"] = filtered_children
            return new_node

        # Leaf and visible
        if node_visible:
            return dict(node)

        return None

    new_menu = dict(menu)
    new_items = []
    for item in menu.get("items", []):
        fi = filter_node(item)
        if fi:
            new_items.append(fi)
    new_menu["items"] = new_items
    return new_menu
