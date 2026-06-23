from django.contrib import admin

from .models import (
    AgPayMerchant,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    StripeWebhookEvent,
)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("name", "sku", "unit_amount", "currency", "requires_shipping", "is_active", "sort_order")


@admin.register(AgPayMerchant)
class AgPayMerchantAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "slug",
        "tenant",
        "legal_entity",
        "stripe_account_id",
        "charges_enabled",
        "payouts_enabled",
        "is_active",
    )
    list_filter = ("is_active", "charges_enabled", "payouts_enabled", "onboarding_completed")
    search_fields = ("display_name", "slug", "tenant__name", "stripe_account_id")
    autocomplete_fields = ("tenant", "legal_entity")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "merchant", "slug", "is_active", "created_at")
    list_filter = ("is_active", "merchant")
    search_fields = ("name", "slug", "merchant__display_name", "merchant__slug")
    autocomplete_fields = ("merchant",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("name", "product", "sku", "unit_amount", "currency", "requires_shipping", "is_active")
    list_filter = ("is_active", "currency", "requires_shipping")
    search_fields = ("name", "sku", "product__name", "product__merchant__slug")
    autocomplete_fields = ("product",)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("line_subtotal",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant", "status", "buyer_email", "external_reference", "created_at")
    list_filter = ("status", "merchant")
    search_fields = ("buyer_email", "buyer_name", "external_reference", "merchant__slug")
    autocomplete_fields = ("merchant",)
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("line_subtotal",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "merchant", "status", "buyer_email", "total_amount", "currency", "created_at", "paid_at")
    list_filter = ("status", "merchant", "currency")
    search_fields = (
        "buyer_email",
        "buyer_name",
        "merchant__slug",
        "stripe_checkout_session_id",
        "stripe_payment_intent_id",
    )
    autocomplete_fields = ("merchant", "cart")
    readonly_fields = ("created_at", "updated_at", "paid_at")
    inlines = [OrderItemInline]


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "status", "received_at", "processed_at")
    list_filter = ("status", "event_type")
    search_fields = ("event_id", "event_type")
    readonly_fields = ("event_id", "event_type", "payload", "received_at", "processed_at", "error")
