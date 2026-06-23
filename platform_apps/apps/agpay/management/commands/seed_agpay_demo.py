from decimal import Decimal

from django.core.management.base import BaseCommand

from platform_apps.apps.agpay.models import AgPayMerchant, Product, ProductVariant
from platform_apps.apps.tenants.models import LegalEntity, Tenant


class Command(BaseCommand):
    help = "Seed a demo AgPay merchant and checkout product."

    def add_arguments(self, parser):
        parser.add_argument("--merchant", default="meatloversca", help="Merchant slug.")
        parser.add_argument("--name", default="MeatLovers.ca", help="Merchant display name.")

    def handle(self, *args, **options):
        merchant_slug = options["merchant"]
        merchant_name = options["name"]

        tenant, _ = Tenant.objects.get_or_create(slug=merchant_slug, defaults={"name": merchant_name})
        legal_entity, _ = LegalEntity.objects.get_or_create(
            tenant=tenant,
            code="MAIN",
            defaults={"name": merchant_name, "default_currency": "CAD"},
        )
        merchant, _ = AgPayMerchant.objects.get_or_create(
            slug=merchant_slug,
            defaults={
                "tenant": tenant,
                "legal_entity": legal_entity,
                "display_name": merchant_name,
                "support_email": "",
                "default_currency": "CAD",
                "platform_fee_bps": 250,
            },
        )

        product, _ = Product.objects.get_or_create(
            merchant=merchant,
            slug="founders-beef-box",
            defaults={
                "name": "Founders Beef Box",
                "description": "Reserve a freezer-ready local beef box from MeatLovers.ca.",
            },
        )
        variant, _ = ProductVariant.objects.get_or_create(
            product=product,
            sku="ML-BEEF-FOUNDERS",
            defaults={
                "name": "Deposit",
                "unit_amount": Decimal("100.00"),
                "currency": "CAD",
                "requires_shipping": False,
            },
        )

        self.stdout.write(self.style.SUCCESS(f"Merchant: {merchant.slug}"))
        self.stdout.write(self.style.SUCCESS(f"Product: {product.slug}"))
        self.stdout.write(self.style.SUCCESS(f"Variant: {variant.sku}"))
        self.stdout.write(f"Checkout page: /agpay/m/{merchant.slug}/products/{product.slug}/")
