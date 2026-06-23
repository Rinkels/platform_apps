from django.contrib import admin
from .models import CatalogItem, CatalogBundle, BundleLine, Quote, QuoteLine, QuoteSnapshot, QuoteAcceptance

@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = ("name", "item_type", "cost_type", "base_price", "currency", "is_active")
    search_fields = ("name",)
    list_filter = ("item_type", "cost_type", "is_active")

class BundleLineInline(admin.TabularInline):
    model = BundleLine
    extra = 0

@admin.register(CatalogBundle)
class CatalogBundleAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    inlines = [BundleLineInline]

class QuoteLineInline(admin.TabularInline):
    model = QuoteLine
    extra = 0

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "currency", "created_at", "sent_at", "accepted_at")
    list_filter = ("status", "currency")
    inlines = [QuoteLineInline]

@admin.register(QuoteSnapshot)
class QuoteSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "quote", "created_at")

@admin.register(QuoteAcceptance)
class QuoteAcceptanceAdmin(admin.ModelAdmin):
    list_display = ("quote", "accepted_name", "accepted_at")
