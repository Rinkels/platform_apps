# apps/accounts/api.py

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from platform_apps.apps.accounts.models import Membership, UserContext
from platform_apps.apps.tenants.models import Tenant, LegalEntity
from platform_apps.apps.tenants.services.resolution import resolve_scope_for_user


def _memberships_payload(user, active_tenant=None, active_legal_entity=None):
    memberships_qs = (
        Membership.objects
        .filter(user=user, is_active=True)
        .select_related("tenant")
        .prefetch_related("legal_entities")
        .order_by("tenant__name")
    )

    memberships = []
    for m in memberships_qs:
        # Allowed LEs:
        # - If membership.legal_entities has rows => restrict to those
        # - Else allow all active LEs for tenant
        if m.legal_entities.exists():
            allowed_les = m.legal_entities.filter(tenant=m.tenant)
        else:
            allowed_les = LegalEntity.objects.filter(tenant=m.tenant, is_active=True)

        memberships.append({
            "tenant": {
                "id": m.tenant.id,
                "slug": getattr(m.tenant, "slug", None),
                "name": getattr(m.tenant, "name", None),
            },
            "is_active_tenant": bool(active_tenant and m.tenant_id == active_tenant.id),
            "allowed_legal_entities": [
                {
                    "id": le.id,
                    "code": getattr(le, "code", None),
                    "name": getattr(le, "name", None),
                    "is_active_legal_entity": bool(active_legal_entity and le.id == active_legal_entity.id),
                }
                for le in allowed_les.order_by("code")
            ],
        })

    return memberships


def _context_payload(user):
    scope = resolve_scope_for_user(user, persist=True)
    tenant = scope.tenant
    le = scope.legal_entity
    ctx = scope.user_context

    return {
        "changed": scope.changed,
        "tenant": None if not tenant else {
            "id": tenant.id,
            "slug": getattr(tenant, "slug", None),
            "name": getattr(tenant, "name", None),
        },
        "legal_entity": None if not le else {
            "id": le.id,
            "code": getattr(le, "code", None),
            "name": getattr(le, "name", None),
        },
        "user_context": None if not ctx else {
            "id": ctx.id,
            "active_tenant_id": ctx.active_tenant_id,
            "active_legal_entity_id": ctx.active_legal_entity_id,
        },
        "memberships": _memberships_payload(user, active_tenant=tenant, active_legal_entity=le),
    }

def _validate_target_scope_or_error(user, tenant_id, legal_entity_id):
    memberships_qs = (
        Membership.objects
        .filter(user=user, is_active=True)
        .select_related("tenant")
        .prefetch_related("legal_entities")
    )

    if not tenant_id:
        return None, None, "tenant_id is required."

    tenant = Tenant.objects.filter(id=tenant_id).first()
    if not tenant:
        return None, None, "Invalid tenant_id."

    if not memberships_qs.filter(tenant=tenant).exists():
        return None, None, "You do not have access to that tenant."

    # legal_entity_id is optional
    legal_entity = None
    if legal_entity_id:
        legal_entity = LegalEntity.objects.filter(id=legal_entity_id, tenant=tenant).first()
        if not legal_entity:
            return None, None, "Invalid legal_entity_id for the selected tenant."

        m = memberships_qs.filter(tenant=tenant).first()
        if m and m.legal_entities.exists() and not m.legal_entities.filter(id=legal_entity.id).exists():
            return None, None, "You do not have access to that legal entity."

    return tenant, legal_entity, None



@require_http_methods(["GET", "POST"])
@login_required
def api_context(request):
    """
    GET: returns resolved context + memberships
    POST: sets context (tenant/legal_entity), then returns updated context + memberships

    POST body can be form-encoded or JSON-like via request.POST (simplest for now):
      tenant_id=<uuid/int>
      legal_entity_id=<uuid/int> (optional)
    """
    if request.method == "GET":
        return JsonResponse(_context_payload(request.user))

    # POST: set requested scope
    tenant_id = (request.POST.get("tenant_id") or "").strip()
    legal_entity_id = (request.POST.get("legal_entity_id") or "").strip()

    tenant, legal_entity, error = _validate_target_scope_or_error(
        request.user,
        tenant_id=tenant_id,
        legal_entity_id=legal_entity_id,
    )

    if error:
        return JsonResponse(
            {
                "error": error,
                "requested": {
                    "tenant_id": tenant_id or None,
                    "legal_entity_id": legal_entity_id or None,
                },
                # useful for UI recovery
                "current": _context_payload(request.user),
            },
            status=400,
        )

    ctx, _ = UserContext.objects.get_or_create(user=request.user)
    ctx.active_tenant = tenant
    ctx.active_legal_entity = legal_entity
    ctx.save(update_fields=["active_tenant", "active_legal_entity", "updated_at"])

    return JsonResponse(_context_payload(request.user))
