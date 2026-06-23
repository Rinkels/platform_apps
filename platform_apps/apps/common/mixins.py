from django.core.exceptions import ImproperlyConfigured
from django.http import Http404

class TenantAwareViewMixin:
    """
    Expects request.tenant (or similar) to be set by middleware.
    Automatically filters queryset by tenant if model has a 'tenant' field.
    """
    tenant_attr = "tenant"  # where the tenant lives on request

    def get_tenant(self):
        tenant = getattr(self.request, self.tenant_attr, None)
        if tenant is None:
            # choose your behavior:
            # - raise ImproperlyConfigured (dev-time)
            # - or 404 (production-safe)
            raise ImproperlyConfigured("request.tenant is not set. Check tenant middleware.")
        return tenant

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = self.get_tenant()

        # If the model is tenant-aware, scope it
        model = getattr(qs, "model", None)
        if model and any(f.name == "tenant" for f in model._meta.fields):
            return qs.filter(tenant=tenant)
        return qs