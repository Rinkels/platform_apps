# apps/accounts/middleware.py

from django.utils.functional import SimpleLazyObject

from platform_apps.apps.tenants.services.resolution import resolve_scope_for_user
from platform_apps.apps.tenants.models import Tenant, LegalEntity


class TenantResolutionMiddleware:
    """
    Canonical request scoping middleware.

    Adds:
      request.user_context
      request.tenant
      request.legal_entity
      request.scope
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        scope = SimpleLazyObject(lambda: resolve_scope_for_user(request.user))

        def _get_tenant():
            tenant_id = request.session.get("tenant_id")
            if tenant_id:
                t = Tenant.objects.filter(id=tenant_id, is_active=True).first()
                if t:
                    return t
            return getattr(scope, "tenant", None)

        def _get_legal_entity():
            entity_id = request.session.get("legal_entity_id")
            tenant = _get_tenant()

            if entity_id:
                le_qs = LegalEntity.objects.filter(id=entity_id)
                if tenant:
                    le_qs = le_qs.filter(tenant=tenant)
                le = le_qs.first()
                if le:
                    return le

            # fallback to whatever resolve_scope_for_user gives us
            le = getattr(scope, "legal_entity", None)
            if le and tenant and getattr(le, "tenant_id", None) != tenant.id:
                return None
            return le

        request.user_context = SimpleLazyObject(lambda: getattr(scope, "user_context", None))
        request.tenant = SimpleLazyObject(_get_tenant)
        request.legal_entity = SimpleLazyObject(_get_legal_entity)
        request.scope = scope

        return self.get_response(request)
