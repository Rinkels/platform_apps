# apps/common/view_mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404


class TenantContextRequiredMixin(LoginRequiredMixin):
    """
    Ensures request.tenant is set via UserContextMiddleware.
    Provides self.tenant and self.legal_entity.
    """
    def dispatch(self, request, *args, **kwargs):
        self.tenant = getattr(request, "tenant", None)
        self.legal_entity = getattr(request, "legal_entity", None)

        if not self.tenant:
            raise Http404("Tenant context not set. Please select a tenant.")

        return super().dispatch(request, *args, **kwargs)


class TenantQuerysetMixin:
    """
    For class-based views: auto-filter queryset by tenant.
    """
    tenant_field = "tenant"

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, "tenant", None)
        if not tenant:
            return qs.none()
        return qs.filter(**{self.tenant_field: tenant})
