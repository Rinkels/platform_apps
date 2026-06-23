# dealermaster/apps/tenants/models.py
from django.db import models
from platform_apps.apps.common.models import TimeStampedModel, SoftDeleteModel

class Tenant(TimeStampedModel, SoftDeleteModel):
    """
    A dealer organization (top-level tenant).
    """
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name


class LegalEntity(TimeStampedModel, SoftDeleteModel):
    """
    A legal company inside a tenant, with separate accounting books.
    """
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="legal_entities")

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)  # e.g. "BR01"
    default_currency = models.CharField(max_length=10, default="CAD")

    class Meta:
        unique_together = [("tenant", "code")]

    def __str__(self):
        return f"{self.tenant.slug}:{self.code} {self.name}"

    @property
    def display_name(self):
        return f"{self.code} - {self.name}"
