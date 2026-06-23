from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

from platform_apps.apps.common.models import TimeStampedModel
from platform_apps.apps.tenants.models import Tenant, LegalEntity


class Membership(TimeStampedModel):
    """
    Grants a user access to a Tenant and optionally a subset of LegalEntities.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="memberships")
    legal_entities = models.ManyToManyField(LegalEntity, blank=True, related_name="memberships")

    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("user", "tenant")]

    # NOTE: legal_entities (M2M) can't be validated on the model — it isn't
    # available until the row has a pk. That validation lives in
    # MembershipAdminForm.clean() (see accounts/admin.py).

    def __str__(self):
        return f"{self.user} -> {self.tenant.slug}"


class UserContext(TimeStampedModel):
    """
    Stores the user's currently selected Tenant and LegalEntity (books).
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="context")

    active_tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, null=True, blank=True)
    active_legal_entity = models.ForeignKey(LegalEntity, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return f"{self.user} ctx {self.active_tenant_id}/{self.active_legal_entity_id}"

    """@SECURITY: This directly protects the invariant implied by your model relationships. """
    def clean(self):
        super().clean()
        if self.active_tenant and self.active_legal_entity:
            if self.active_legal_entity.tenant_id != self.active_tenant_id:
                raise ValidationError("Active LegalEntity must belong to the active Tenant.")
