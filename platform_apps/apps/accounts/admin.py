# apps/accounts/admin.py

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Membership, UserContext
from platform_apps.apps.tenants.models import LegalEntity


class MembershipAdminForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        tenant = cleaned.get("tenant")
        legal_entities = cleaned.get("legal_entities")

        if tenant and legal_entities:
            bad = [le for le in legal_entities if le.tenant_id != tenant.id]
            if bad:
                raise ValidationError(
                    "One or more Legal Entities do not belong to the selected Tenant: "
                    + ", ".join([f"{le.code}" for le in bad])
                )
        return cleaned


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    form = MembershipAdminForm
    list_display = ("user", "tenant", "is_admin", "is_active", "created_at")
    list_filter = ("tenant", "is_admin", "is_active")
    search_fields = ("user__username", "user__email", "tenant__name", "tenant__slug")
    autocomplete_fields = ("user", "tenant", "legal_entities")


@admin.register(UserContext)
class UserContextAdmin(admin.ModelAdmin):
    list_display = ("user", "active_tenant", "active_legal_entity", "updated_at")
    list_filter = ("active_tenant", "active_legal_entity")
    search_fields = ("user__username", "user__email")
    autocomplete_fields = ("user", "active_tenant", "active_legal_entity")
