# apps/common/management/commands/seed_core.py

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.db import transaction

from apps.tenants.models import Tenant, LegalEntity
from apps.locations.models import Location, Pen
from apps.parties.models import Party
from apps.inventory.models import InventoryLot


class Command(BaseCommand):
    help = "Seed core reference data for DealerMaster (tenant, entities, locations, pens, parties, sample lot)."

    @transaction.atomic
    def handle(self, *args, **options):
        tenant_name = "McCall Livestock"
        tenant_slug = slugify(tenant_name)

        tenant, tenant_created = Tenant.objects.get_or_create(
            slug=tenant_slug,
            defaults={"name": tenant_name},
        )

        self.stdout.write(self.style.SUCCESS(
            f"Tenant: {tenant.name} ({'created' if tenant_created else 'exists'})"
        ))

        # --- Legal Entities (separate books) ---
        le1, le1_created = LegalEntity.objects.get_or_create(
            tenant=tenant,
            code="MCL01",
            defaults={"name": "McCall Livestock Ltd.", "default_currency": "CAD"},
        )

        le2, le2_created = LegalEntity.objects.get_or_create(
            tenant=tenant,
            code="MCL02",
            defaults={"name": "McCall Livestock (Trading) Ltd.", "default_currency": "CAD"},
        )

        self.stdout.write(self.style.SUCCESS(
            f"LegalEntity: {le1.code} ({'created' if le1_created else 'exists'})"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"LegalEntity: {le2.code} ({'created' if le2_created else 'exists'})"
        ))

        # --- Locations ---
        loc_feedlot, loc_feedlot_created = Location.objects.get_or_create(
            tenant=tenant,
            code="FL01",
            defaults={"name": "McCall Feedlot", "address": "TBD"},
        )
        loc_yard, loc_yard_created = Location.objects.get_or_create(
            tenant=tenant,
            code="YD01",
            defaults={"name": "McCall Yard", "address": "TBD"},
        )

        self.stdout.write(self.style.SUCCESS(
            f"Location: {loc_feedlot.code} ({'created' if loc_feedlot_created else 'exists'})"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Location: {loc_yard.code} ({'created' if loc_yard_created else 'exists'})"
        ))

        # --- Pens ---
        pen_a, pen_a_created = Pen.objects.get_or_create(
            tenant=tenant,
            location=loc_feedlot,
            code="A",
            defaults={"name": "Pen A"},
        )
        pen_b, pen_b_created = Pen.objects.get_or_create(
            tenant=tenant,
            location=loc_feedlot,
            code="B",
            defaults={"name": "Pen B"},
        )
        pen_y1, pen_y1_created = Pen.objects.get_or_create(
            tenant=tenant,
            location=loc_yard,
            code="Y1",
            defaults={"name": "Yard Pen 1"},
        )

        self.stdout.write(self.style.SUCCESS(f"Pen: {pen_a} ({'created' if pen_a_created else 'exists'})"))
        self.stdout.write(self.style.SUCCESS(f"Pen: {pen_b} ({'created' if pen_b_created else 'exists'})"))
        self.stdout.write(self.style.SUCCESS(f"Pen: {pen_y1} ({'created' if pen_y1_created else 'exists'})"))

        # --- Parties (customers/vendors) ---
        cust, cust_created = Party.objects.get_or_create(
            tenant=tenant,
            code="CUST001",
            defaults={"name": "Example Buyer Inc.", "party_type": "CUSTOMER"},
        )
        vend, vend_created = Party.objects.get_or_create(
            tenant=tenant,
            code="VEND001",
            defaults={"name": "Example Ranch", "party_type": "VENDOR"},
        )

        self.stdout.write(self.style.SUCCESS(f"Party: {cust} ({'created' if cust_created else 'exists'})"))
        self.stdout.write(self.style.SUCCESS(f"Party: {vend} ({'created' if vend_created else 'exists'})"))

        # --- Sample Inventory Lot ---
        lot, lot_created = InventoryLot.objects.get_or_create(
            tenant=tenant,
            legal_entity=le1,
            lot_tag="LOT-0001",
            defaults={
                "kind": "STRS",
                "head_count": 50,
                "total_weight": 55000,
                "avg_weight": 1100,
                "current_pen": pen_a,
                "cost_amount": 125000.00,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            f"InventoryLot: {lot} ({'created' if lot_created else 'exists'})"
        ))

        self.stdout.write(self.style.SUCCESS("✅ Seed complete."))
