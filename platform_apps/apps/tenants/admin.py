# dealermaster/apps/tenants/admin.py

from django.contrib import admin
from .models import Tenant, LegalEntity


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(LegalEntity)
class LegalEntityAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "tenant", "default_currency", "is_active", "created_at")
    list_filter = ("tenant", "is_active", "default_currency")
    search_fields = ("code", "name", "tenant__name", "tenant__slug")
    ordering = ("tenant__name", "code")
    autocomplete_fields = ("tenant",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Core", {
            "fields": (
                ("tenant",),
                ("code", "name"),
                "default_currency",
                "is_active",
            )
        }),
        ("System", {
            "fields": ("created_at", "updated_at"),
        }),
    )
