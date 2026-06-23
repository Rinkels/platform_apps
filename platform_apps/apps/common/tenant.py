# apps/common/tenant.py
from django.db import models

from platform_apps.apps.common.models import TimeStampedModel


class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        if tenant is None:
            return self.none()
        return self.filter(tenant=tenant)

    def create(self, **kwargs):
        if hasattr(self, "_tenant") and "tenant" not in kwargs:
            kwargs["tenant"] = self._tenant
        return super().create(**kwargs)

    def get_or_create(self, defaults=None, **kwargs):
        defaults = defaults or {}
        if hasattr(self, "_tenant"):
            kwargs.setdefault("tenant", self._tenant)
            defaults.setdefault("tenant", self._tenant)
        return super().get_or_create(defaults=defaults, **kwargs)


class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant):
        return self.get_queryset().for_tenant(tenant)


class TenantAwareModel(TimeStampedModel):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        db_index=True,
    )

    objects = TenantManager()

    class Meta:
        abstract = True
