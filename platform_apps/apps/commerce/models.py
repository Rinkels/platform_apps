from decimal import Decimal
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.db.models import Q

CURRENCY_DEFAULT = getattr(settings, "COMMERCE_DEFAULT_CURRENCY", "CAD")

COST_TYPE_CHOICES = [
    ("one_time", "One Time"),
    ("per_month", "Monthly"),
    ("per_year", "Annually"),
    ("per_week", "Weekly"),
    ("per_quarter", "Quarterly"),
]

ITEM_TYPE_CHOICES = [
    ("service", "Service"),
    ("hardware", "Hardware"),
    ("fee", "Fee"),
    ("discount", "Discount"),
    ("credit", "Credit"),
]

QUOTE_STATUS_CHOICES = [
    ("draft", "Draft"),
    ("sent", "Sent"),
    ("accepted", "Accepted"),
    ("expired", "Expired"),
    ("void", "Void"),
]

def _org_fk_kwargs():
    """
    If you define COMMERCE_ORG_MODEL in settings, we attach org scoping.
    Example: COMMERCE_ORG_MODEL = "common.Organization"
    """
    org_model = getattr(settings, "COMMERCE_ORG_MODEL", None)
    if not org_model:
        return None
    return dict(to=org_model, on_delete=models.PROTECT, related_name="%(class)s_set")

class CatalogItem(models.Model):
    org = models.ForeignKey(**_org_fk_kwargs()) if _org_fk_kwargs() else None

    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default="service")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sku = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text="Internal SKU / product code. Optional, but recommended for stable imports."
    )

    unit_label = models.CharField(max_length=64, blank=True, help_text="e.g. per user, per device, per domain")
    cost_type = models.CharField(max_length=20, choices=COST_TYPE_CHOICES, default="per_month")

    currency = models.CharField(max_length=8, default=CURRENCY_DEFAULT)
    base_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    tax_rate = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0.0000"))  # e.g. 0.05 GST
    is_taxable = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    tags = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["item_type", "cost_type"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["org", "sku"],
                name="uniq_commerce_catalogitem_org_sku",
                condition=Q(sku__isnull=False) & ~Q(sku=""),
            ),
        ]

    def __str__(self):
        return self.name


class CatalogBundle(models.Model):
    org = models.ForeignKey(**_org_fk_kwargs()) if _org_fk_kwargs() else None

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    tags = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class BundleLine(models.Model):
    bundle = models.ForeignKey(CatalogBundle, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(CatalogItem, on_delete=models.PROTECT)
    default_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("1.00"))
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.bundle} -> {self.item}"


class Quote(models.Model):
    org = models.ForeignKey(**_org_fk_kwargs()) if _org_fk_kwargs() else None

    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=QUOTE_STATUS_CHOICES, default="draft")

    currency = models.CharField(max_length=8, default=CURRENCY_DEFAULT)
    default_tax_rate = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0.0500"))  # GST default

    # Link to ANY CRM/company object in any project (nurbai/fractals/dealermaster)
    company_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    company_object_id = models.CharField(max_length=64, null=True, blank=True)
    company = GenericForeignKey("company_content_type", "company_object_id")

    created_by_id = models.CharField(max_length=64, blank=True)  # optional, keep generic across projects
    created_at = models.DateTimeField(auto_now_add=True)

    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Quote #{self.id} {self.title}".strip()


class QuoteLine(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="lines")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")

    catalog_item = models.ForeignKey(CatalogItem, on_delete=models.PROTECT, null=True, blank=True)
    label = models.CharField(max_length=255)  # snapshot-friendly display label
    description = models.TextField(blank=True)

    cost_type = models.CharField(max_length=20, choices=COST_TYPE_CHOICES, default="per_month")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    is_selected = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)

    tax_rate = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0.0000"))
    is_taxable = models.BooleanField(default=True)

    # Explains “why this line exists” (rules engine later)
    rule_context = models.JSONField(default=dict, blank=True)

    sort_order = models.IntegerField(default=0)

    def line_subtotal(self) -> Decimal:
        if not self.is_selected:
            return Decimal("0.00")
        return (self.unit_price or Decimal("0.00")) * (self.quantity or Decimal("0.00"))

    def __str__(self):
        return self.label


class QuoteSnapshot(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="snapshots")
    created_at = models.DateTimeField(auto_now_add=True)

    # Immutable snapshot for PDF + audit
    payload = models.JSONField(default=dict)

    def __str__(self):
        return f"Snapshot {self.id} for Quote {self.quote_id}"


class QuoteAcceptance(models.Model):
    quote = models.OneToOneField(Quote, on_delete=models.CASCADE, related_name="acceptance")
    accepted_name = models.CharField(max_length=255)
    accepted_email = models.EmailField(blank=True)
    accepted_at = models.DateTimeField(default=timezone.now)
    signature_meta = models.JSONField(default=dict, blank=True)  # ip, user-agent, etc.

    def __str__(self):
        return f"Accepted Quote {self.quote_id} by {self.accepted_name}"
