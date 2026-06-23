from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from platform_apps.apps.tenants.models import LegalEntity, Tenant


CURRENCY_DEFAULT = "CAD"


class AgPayMerchant(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="agpay_merchants")
    legal_entity = models.ForeignKey(
        LegalEntity,
        on_delete=models.PROTECT,
        related_name="agpay_merchants",
        null=True,
        blank=True,
    )

    slug = models.SlugField(max_length=120, unique=True)
    display_name = models.CharField(max_length=200)
    support_email = models.EmailField(blank=True)
    default_currency = models.CharField(max_length=8, default=CURRENCY_DEFAULT)

    stripe_account_id = models.CharField(max_length=128, blank=True, db_index=True)
    charges_enabled = models.BooleanField(default=False)
    payouts_enabled = models.BooleanField(default=False)
    onboarding_completed = models.BooleanField(default=False)
    platform_fee_bps = models.PositiveIntegerField(default=250, help_text="Platform fee in basis points. 250 = 2.5%.")

    success_url = models.URLField(blank=True, help_text="Optional merchant-branded success URL.")
    cancel_url = models.URLField(blank=True, help_text="Optional merchant-branded cancel URL.")

    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("display_name",)

    def __str__(self):
        return self.display_name


class Product(models.Model):
    merchant = models.ForeignKey(AgPayMerchant, on_delete=models.PROTECT, related_name="products")
    slug = models.SlugField(max_length=140)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("merchant", "name")
        constraints = [
            models.UniqueConstraint(fields=["merchant", "slug"], name="uniq_agpay_product_merchant_slug"),
        ]

    def __str__(self):
        return f"{self.merchant.slug}: {self.name}"

    def get_absolute_url(self):
        return reverse("agpay:product_detail", args=[self.merchant.slug, self.slug])


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=255)
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default=CURRENCY_DEFAULT)
    requires_shipping = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ("product", "sort_order", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["product", "sku"],
                name="uniq_agpay_variant_product_sku",
                condition=Q(sku__isnull=False) & ~Q(sku=""),
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def amount_cents(self) -> int:
        return int((self.unit_amount or Decimal("0.00")) * 100)


class Cart(models.Model):
    STATUS_OPEN = "open"
    STATUS_CHECKOUT = "checkout"
    STATUS_ORDERED = "ordered"
    STATUS_ABANDONED = "abandoned"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_CHECKOUT, "Checkout"),
        (STATUS_ORDERED, "Ordered"),
        (STATUS_ABANDONED, "Abandoned"),
    ]

    merchant = models.ForeignKey(AgPayMerchant, on_delete=models.PROTECT, related_name="carts")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    buyer_email = models.EmailField(blank=True)
    buyer_name = models.CharField(max_length=255, blank=True)
    external_reference = models.CharField(max_length=128, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.id} - {self.merchant.slug}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    label = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default=CURRENCY_DEFAULT)
    metadata = models.JSONField(default=dict, blank=True)

    def line_subtotal(self) -> Decimal:
        return (self.unit_amount or Decimal("0.00")) * Decimal(self.quantity or 0)

    def __str__(self):
        return f"{self.quantity} x {self.label}"


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_CANCELLED = "cancelled"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    merchant = models.ForeignKey(AgPayMerchant, on_delete=models.PROTECT, related_name="orders")
    cart = models.ForeignKey(Cart, on_delete=models.SET_NULL, related_name="orders", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    buyer_email = models.EmailField(blank=True)
    buyer_name = models.CharField(max_length=255, blank=True)
    currency = models.CharField(max_length=8, default=CURRENCY_DEFAULT)
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    platform_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Order {self.id} - {self.merchant.slug} - {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, null=True, blank=True)
    label = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default=CURRENCY_DEFAULT)
    metadata = models.JSONField(default=dict, blank=True)

    def line_subtotal(self) -> Decimal:
        return (self.unit_amount or Decimal("0.00")) * Decimal(self.quantity or 0)

    def __str__(self):
        return f"{self.quantity} x {self.label}"


class StripeWebhookEvent(models.Model):
    STATUS_RECEIVED = "received"
    STATUS_PROCESSED = "processed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_RECEIVED, "Received"),
        (STATUS_PROCESSED, "Processed"),
        (STATUS_FAILED, "Failed"),
    ]

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=120, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RECEIVED)
    payload = models.JSONField(default=dict)
    error = models.TextField(blank=True)
    received_at = models.DateTimeField(default=timezone.now, editable=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-received_at",)

    def __str__(self):
        return f"{self.event_type} ({self.status})"
