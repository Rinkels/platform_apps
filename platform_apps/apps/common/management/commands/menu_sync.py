import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


# ---------- Config / Mapping ----------
DEFAULT_MENU_PATH = "config/menu/menu.json"

# Map "domain" from menu.json -> (python module path for urls.py, url prefix, app_name namespace)
# You can tweak these later without changing the JSON.
DOMAIN_MAP: Dict[str, Dict[str, str]] = {
    "inventory": {"urls_module": "apps.inventory.urls", "prefix": "", "app_name": "inventory"},
    "contacts": {"urls_module": "apps.parties.urls", "prefix": "", "app_name": "parties"},
    "system": {"urls_module": "apps.tenants.urls", "prefix": "system/", "app_name": "tenants"},

    # Accounting submodules
    "ar": {"urls_module": "apps.accounting.ar.urls", "prefix": "", "app_name": "ar"},
    "ap": {"urls_module": "apps.accounting.ap.urls", "prefix": "", "app_name": "ap"},
    "gl": {"urls_module": "apps.accounting.gl.urls", "prefix": "", "app_name": "gl"},

    "purchases": {"urls_module": "apps.purchases.urls", "prefix": "", "app_name": "purchases"},
    "interfaces": {"urls_module": "apps.finance.urls", "prefix": "interfaces/", "app_name": "finance"},
    "finance": {"urls_module": "apps.finance.urls", "prefix": "", "app_name": "finance"},
    "invoicing": {"urls_module": "apps.invoicing.urls", "prefix": "", "app_name": "invoicing"},
    "reports": {"urls_module": "apps.reports.urls", "prefix": "", "app_name": "reports"},
    "dealermaster": {"urls_module": "apps.dashboard.urls", "prefix": "", "app_name": "dashboard"},
}


@dataclass(frozen=True)
class RouteSpec:
    route_name: str            # e.g. "gl:trial_balance"
    url_path: str              # e.g. "trial-balance/"
    view_name: str             # e.g. "trial_balance"
    permission: Optional[str]  # e.g. "gl.report"
    label: str                 # display label
    code: str                  # legacy code


# ---------- Helpers ----------
def project_root() -> Path:
    # manage.py lives in the repo root
    return Path(settings.BASE_DIR).resolve()


def abs_path_from_module(module_path: str) -> Path:
    """
    Convert 'apps.accounting.gl.urls' to filesystem path <repo>/apps/accounting/gl/urls.py
    """
    rel = Path(*module_path.split(".")).with_suffix(".py")
    return project_root() / rel


def slugify_view_name(route_tail: str) -> str:
    # route_tail from route_name after ":"; keep it pythonic
    return route_tail.strip().replace("-", "_")


def derive_url_from_route_tail(route_tail: str, item_type: str) -> str:
    """
    Heuristic for URL patterns:
    - report -> "reports/<tail>/"
    - inquiry -> "inquiry/<tail>/" unless already includes 'inquiry'
    - action/batch -> "actions/<tail>/" or "batch/<tail>/"
    - screen -> "<tail>/"
    """
    tail = route_tail.strip()
    if item_type == "report":
        return f"reports/{tail}/"
    if item_type == "inquiry":
        return f"inquiry/{tail}/"
    if item_type == "action":
        return f"actions/{tail}/"
    if item_type == "batch":
        return f"batch/{tail}/"
    # screen/group fallback
    return f"{tail}/"


def flatten_menu(menu: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def walk(node: Dict[str, Any]) -> None:
        out.append(node)
        for child in node.get("children", []) or []:
            walk(child)

    for item in menu.get("items", []):
        walk(item)
    return out


def extract_routes(menu: Dict[str, Any]) -> List[Tuple[str, RouteSpec]]:
    """
    Returns list of (domain, RouteSpec) for nodes that have route_name.
    """
    routes: List[Tuple[str, RouteSpec]] = []
    for node in flatten_menu(menu):
        route_name = node.get("route_name")
        domain = node.get("domain")
        item_type = node.get("type", "screen")

        if not route_name or not domain:
            continue

        # route_name looks like "gl:trial_balance"
        if ":" not in route_name:
            continue

        ns, tail = route_name.split(":", 1)
        view_name = slugify_view_name(f"{ns}_{tail}")
        url_path = derive_url_from_route_tail(tail, item_type)

        routes.append(
            (domain, RouteSpec(
                route_name=route_name,
                url_path=url_path,
                view_name=view_name,
                permission=node.get("permission"),
                label=node.get("label", ""),
                code=str(node.get("code", "")),
            ))
        )
    return routes


URLS_TEMPLATE = """\
from django.urls import path

from . import views

app_name = "{app_name}"

urlpatterns = [
{patterns}
]
"""

PATTERN_LINE = '    path("{url}", views.{view}, name="{name}"),  # {code} {label}\n'


VIEWS_TEMPLATE = """\
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse

# Auto-generated stubs. Replace with real implementations.


@login_required
def not_implemented(request: HttpRequest, title: str) -> HttpResponse:
    return HttpResponse(f"<h1>{{title}}</h1><p>Not implemented yet.</p>")


{view_functions}
"""

VIEW_FUNC_LINE = """\
@login_required
def {view_name}(request: HttpRequest) -> HttpResponse:
    return not_implemented(request, "{title}")
"""


def ensure_parent_dirs(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


# ---------- Command ----------
class Command(BaseCommand):
    help = "Generate per-app urls.py (and optional stub views.py) from config/menu/menu.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(project_root() / DEFAULT_MENU_PATH),
            help="Path to menu.json (default: dealermaster/config/menu/menu.json)",
        )
        parser.add_argument(
            "--write-views",
            action="store_true",
            help="Also generate stub views.py in each target module folder",
        )

    def handle(self, *args, **options):
        menu_path = Path(options["path"]).resolve()
        if not menu_path.exists():
            raise CommandError(f"menu.json not found at: {menu_path}")

        try:
            menu = json.loads(menu_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise CommandError(f"Failed to parse JSON: {e}")

        routes = extract_routes(menu)
        if not routes:
            self.stdout.write(self.style.WARNING("No routes found in menu.json (no route_name fields?)."))
            return

        # Group by urls_module
        module_to_specs: Dict[str, List[RouteSpec]] = {}
        module_to_app_name: Dict[str, str] = {}
        module_to_prefix: Dict[str, str] = {}

        for domain, spec in routes:
            mapping = DOMAIN_MAP.get(domain)
            if not mapping:
                self.stdout.write(self.style.WARNING(f"Skipping domain '{domain}' (no DOMAIN_MAP entry)"))
                continue

            urls_module = mapping["urls_module"]
            module_to_specs.setdefault(urls_module, []).append(spec)
            module_to_app_name[urls_module] = mapping["app_name"]
            module_to_prefix[urls_module] = mapping.get("prefix", "")

        # Write urls.py per module
        for urls_module, specs in module_to_specs.items():
            specs_sorted = sorted(specs, key=lambda s: (s.route_name, s.url_path))

            urls_file = abs_path_from_module(urls_module)
            ensure_parent_dirs(urls_file)

            prefix = module_to_prefix.get(urls_module, "")
            app_name = module_to_app_name[urls_module]

            patterns = ""
            for s in specs_sorted:
                # name should be the part after namespace
                _, name_tail = s.route_name.split(":", 1)
                url = f"{prefix}{s.url_path}"
                patterns += PATTERN_LINE.format(url=url, view=s.view_name, name=name_tail, code=s.code, label=s.label)

            urls_file.write_text(URLS_TEMPLATE.format(app_name=app_name, patterns=patterns.rstrip()), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote {urls_file} ({len(specs_sorted)} routes)"))

            # Optionally generate stub views
            if options["write_views"]:
                views_file = urls_file.parent / "views.py"
                view_funcs = ""
                for s in specs_sorted:
                    view_funcs += VIEW_FUNC_LINE.format(view_name=s.view_name, title=f"{s.code} {s.label}")

                views_file.write_text(VIEWS_TEMPLATE.format(view_functions=view_funcs.rstrip()), encoding="utf-8")
                self.stdout.write(self.style.SUCCESS(f"Wrote {views_file} (stubs)"))

        self.stdout.write(self.style.SUCCESS("menu_sync complete."))
