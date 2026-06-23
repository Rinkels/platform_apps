import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgPayMerchant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=120, unique=True)),
                ("display_name", models.CharField(max_length=200)),
                ("support_email", models.EmailField(blank=True, max_length=254)),
                ("default_currency", models.CharField(default="CAD", max_length=8)),
                ("stripe_account_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("charges_enabled", models.BooleanField(default=False)),
                ("payouts_enabled", models.BooleanField(default=False)),
                ("onboarding_completed", models.BooleanField(default=False)),
                ("platform_fee_bps", models.PositiveIntegerField(default=250, help_text="Platform fee in basis points. 250 = 2.5%.")),
                ("success_url", models.URLField(blank=True, help_text="Optional merchant-branded success URL.")),
                ("cancel_url", models.URLField(blank=True, help_text="Optional merchant-branded cancel URL.")),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("legal_entity", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="agpay_merchants", to="tenants.legalentity")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="agpay_merchants", to="tenants.tenant")),
            ],
            options={"ordering": ("display_name",)},
        ),
        migrations.CreateModel(
            name="Cart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("open", "Open"), ("checkout", "Checkout"), ("ordered", "Ordered"), ("abandoned", "Abandoned")], default="open", max_length=20)),
                ("buyer_email", models.EmailField(blank=True, max_length=254)),
                ("buyer_name", models.CharField(blank=True, max_length=255)),
                ("external_reference", models.CharField(blank=True, db_index=True, max_length=128)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("merchant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="carts", to="agpay.agpaymerchant")),
            ],
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("paid", "Paid"), ("cancelled", "Cancelled"), ("refunded", "Refunded")], default="pending", max_length=20)),
                ("buyer_email", models.EmailField(blank=True, max_length=254)),
                ("buyer_name", models.CharField(blank=True, max_length=255)),
                ("currency", models.CharField(default="CAD", max_length=8)),
                ("subtotal_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("platform_fee_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("total_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("stripe_checkout_session_id", models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ("stripe_payment_intent_id", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("cart", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orders", to="agpay.cart")),
                ("merchant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="agpay.agpaymerchant")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=140)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("merchant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="agpay.agpaymerchant")),
            ],
            options={"ordering": ("merchant", "name")},
        ),
        migrations.CreateModel(
            name="StripeWebhookEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.CharField(max_length=255, unique=True)),
                ("event_type", models.CharField(db_index=True, max_length=120)),
                ("status", models.CharField(choices=[("received", "Received"), ("processed", "Processed"), ("failed", "Failed")], default="received", max_length=20)),
                ("payload", models.JSONField(default=dict)),
                ("error", models.TextField(blank=True)),
                ("received_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ("-received_at",)},
        ),
        migrations.CreateModel(
            name="ProductVariant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku", models.CharField(blank=True, max_length=80)),
                ("name", models.CharField(max_length=255)),
                ("unit_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("currency", models.CharField(default="CAD", max_length=8)),
                ("requires_shipping", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("sort_order", models.IntegerField(default=0)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variants", to="agpay.product")),
            ],
            options={"ordering": ("product", "sort_order", "name")},
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=255)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="CAD", max_length=8)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="agpay.order")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="agpay.productvariant")),
            ],
        ),
        migrations.CreateModel(
            name="CartItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=255)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="CAD", max_length=8)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("cart", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="agpay.cart")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="agpay.productvariant")),
            ],
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.UniqueConstraint(fields=("merchant", "slug"), name="uniq_agpay_product_merchant_slug"),
        ),
        migrations.AddConstraint(
            model_name="productvariant",
            constraint=models.UniqueConstraint(
                condition=models.Q(sku__isnull=False) & ~models.Q(sku=""),
                fields=("product", "sku"),
                name="uniq_agpay_variant_product_sku",
            ),
        ),
    ]
