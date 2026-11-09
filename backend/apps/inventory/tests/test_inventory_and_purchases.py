from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounting.models import JournalEntry
from apps.core.models import AccountingPeriod, User
from apps.inventory.models import (
    Adjustment,
    InventoryMovement,
    Location,
    Product,
    Stock,
)
from apps.inventory.services import (
    InsufficientStockError,
    RegimeMismatchError,
    create_adjustment,
    get_inventory_summary,
    get_product_kardex,
    register_consumption,
    transfer_stock,
)
from apps.purchases.models import Purchase, Supplier
from apps.purchases.services import (
    create_purchase,
    get_purchase_book,
    register_supplier_payment,
    void_purchase,
)
from apps.reports.services.closing import get_close_preview
from apps.sales.models import Customer, Sale
from apps.sales.services import create_sale


@pytest.mark.django_db
class TestInventoryAndPurchases:
    def test_seeded_inventory_summary_and_ledger_reconciliation(self):
        summary = get_inventory_summary()
        kpis = summary["kpis"]

        assert kpis["vitrina"]["units_total"] == "61"
        assert kpis["vitrina"]["items_count"] == 4
        assert Decimal(kpis["vitrina"]["cost_valuation"]) == Decimal("889.50")
        assert Decimal(kpis["vitrina"]["pvp_valuation"]) == Decimal("746.50")

        assert kpis["cabina"]["units_total"] == "48"
        assert kpis["cabina"]["items_count"] == 4
        assert Decimal(kpis["cabina"]["cost_valuation"]) == Decimal("551.50")

        assert kpis["critical"]["count"] == 2
        assert "Serum" in kpis["critical"]["suggested_restock"]

        # Verify P3 closing check #4 (inventory_matches_ledger) passes
        period = AccountingPeriod.objects.get(year=2026, month=11)
        preview = get_close_preview(period)
        inv_check = next(c for c in preview["checks"] if c["key"] == "inventory_matches_ledger")
        assert inv_check["ok"] is True

    def test_seeded_purchase_book_matches_vista_4_mockup(self):
        period = AccountingPeriod.objects.get(year=2026, month=11)
        book = get_purchase_book(period=period)

        totals = book["totals"]
        assert Decimal(totals["taxable_amount"]) == Decimal("300.00")
        assert Decimal(totals["iva_credit"]) == Decimal("39.00")
        assert Decimal(totals["total"]) == Decimal("339.00")
        assert book["kpis"]["documents_count"] == 3
        assert book["kpis"]["active_suppliers_count"] == 3

        dist = book["distribution"]
        assert Decimal(dist["vitrina_amount"]) == Decimal("169.50")
        assert dist["vitrina_pct"] == 50
        assert Decimal(dist["cabina_amount"]) == Decimal("169.50")
        assert dist["cabina_pct"] == 50

    def test_create_purchase_updates_weighted_average_cost_and_posts_entry(self):
        user = User.objects.filter(role=User.Role.ADMIN).first()
        supplier = Supplier.objects.filter(name="Distribuidora Bella").first()
        product = Product.objects.get(sku="VIT-001")
        # Initial VIT-001: 18 u @ $7.0000 cost = $126.00

        purchase = create_purchase(
            supplier_id=supplier.id,
            doc_type="CCF",
            doc_number="CCF-4599",
            doc_date=date(2026, 11, 10),
            due_date=date(2026, 11, 25),
            destination="VITRINA",
            payment_condition="CREDIT",
            lines=[
                {
                    "product_id": product.id,
                    "description": "Compra adicional Champú nutritivo",
                    "quantity": "6.000",
                    "unit_cost": "11.0000",
                }
            ],
            notes="Reabastecimiento vitrina",
            user=user,
        )

        # Subtotal = 6 * 11 = 66.00, IVA = 8.58, Total = 74.58
        assert purchase.taxable_amount == Decimal("66.00")
        assert purchase.iva_credit == Decimal("8.58")
        assert purchase.total == Decimal("74.58")
        assert purchase.journal_entry is not None
        assert purchase.journal_entry.status == JournalEntry.EntryStatus.POSTED

        # Weighted average cost: (18 * 7.00 + 6 * 11.00) / 24 = (126 + 66) / 24 = 192 / 24 = 8.0000
        product.refresh_from_db()
        assert product.average_cost == Decimal("8.0000")
        kardex = get_product_kardex(product.id)
        assert Decimal(kardex["product"]["current_stock"]) == Decimal("24.000")

        # Test supplier payment on credit purchase
        payment = register_supplier_payment(
            purchase=purchase,
            payment_date=date(2026, 11, 12),
            amount=Decimal("74.58"),
            payment_method="TRANSFER",
            reference="TRF-9988",
            user=user,
        )
        purchase.refresh_from_db()
        assert purchase.payment_status == Purchase.PaymentStatus.PAID
        assert payment.journal_entry is not None

    def test_void_purchase_reverses_stock_and_journal_entry(self):
        user = User.objects.filter(role=User.Role.ADMIN).first()
        supplier = Supplier.objects.filter(name="Insumos Pro").first()
        product = Product.objects.get(sku="CAB-001")

        purchase = create_purchase(
            supplier_id=supplier.id,
            doc_type="CCF",
            doc_number="CCF-4605",
            doc_date=date(2026, 11, 11),
            destination="CABINA",
            payment_condition="CREDIT",
            lines=[
                {
                    "product_id": product.id,
                    "description": "Compra tinte cabina",
                    "quantity": "5.000",
                    "unit_cost": "15.0000",
                }
            ],
            user=user,
        )
        assert Stock.objects.filter(product=product).first().quantity == Decimal("14.000")

        voided = void_purchase(purchase, reason="Error en facturación", user=user)
        assert voided.status == Purchase.Status.VOIDED
        voided.journal_entry.refresh_from_db()
        assert voided.journal_entry.status == JournalEntry.EntryStatus.REVERSED
        assert Stock.objects.filter(product=product).first().quantity == Decimal("9.000")

    def test_negative_stock_blocked_and_rn07_enforced(self):
        user = User.objects.filter(role=User.Role.ADMIN).first()
        cabina_product = Product.objects.get(sku="CAB-002")  # 5 u in Cabina 2
        vitrina_product = Product.objects.get(sku="VIT-003")  # 7 u in Vitrina

        # Attempting to consume more than 5 u raises InsufficientStockError
        with pytest.raises(InsufficientStockError):
            register_consumption(
                consumption_date=date(2026, 11, 12),
                location="CAB2",
                lines=[{"product_id": cabina_product.id, "quantity": "10.000"}],
                user=user,
            )

        # Attempting to consume a Vitrina retail product as Cabina supply violates RN-07
        with pytest.raises(RegimeMismatchError):
            register_consumption(
                consumption_date=date(2026, 11, 12),
                location="CAB1",
                lines=[{"product_id": vitrina_product.id, "quantity": "1.000"}],
                user=user,
            )

    def test_adjustment_consumption_and_transfer_post_accounting_entries(self):
        user = User.objects.filter(role=User.Role.ADMIN).first()
        vitrina_product = Product.objects.get(sku="VIT-004")  # 25 u @ $17.04
        cabina_product = Product.objects.get(sku="CAB-001")  # 9 u @ $15.00 in Cabina 1
        loc_cab2 = Location.objects.get(code="CAB2")

        # 1. Negative adjustment on VIT-004 (-2 u) -> Debe 420102 / Haber 110501
        adj = create_adjustment(
            adjustment_date=date(2026, 11, 14),
            reason=Adjustment.Reason.DAMAGE,
            lines=[
                {
                    "product_id": vitrina_product.id,
                    "location": "VIT",
                    "direction": "OUT",
                    "quantity": "2.000",
                }
            ],
            notes="Envase roto en exhibición",
            user=user,
        )
        assert adj.journal_entry is not None
        assert Stock.objects.get(product=vitrina_product, location__code="VIT").quantity == Decimal("23.000")

        # 2. Cabina consumption on CAB-001 (2 u) -> Debe 410201 / Haber 110502 ($30.00)
        cons = register_consumption(
            consumption_date=date(2026, 11, 14),
            location="CAB1",
            lines=[{"product_id": cabina_product.id, "quantity": "2.000"}],
            notes="Tinte completo cliente",
            user=user,
        )
        assert cons.journal_entry is not None
        assert Stock.objects.get(product=cabina_product, location__code="CAB1").quantity == Decimal("7.000")

        # 3. Transfer CAB-001 (3 u) from Cabina 1 to Cabina 2
        res = transfer_stock(
            transfer_date=date(2026, 11, 14),
            product=cabina_product,
            from_location="CAB1",
            to_location=loc_cab2,
            quantity=Decimal("3.000"),
            user=user,
        )
        assert res["movement_out_id"] is not None
        assert Stock.objects.get(product=cabina_product, location__code="CAB1").quantity == Decimal("4.000")
        assert Stock.objects.get(product=cabina_product, location__code="CAB2").quantity == Decimal("3.000")

    def test_sale_of_vitrina_product_deducts_stock_and_posts_cogs(self):
        user = User.objects.filter(role=User.Role.ADMIN).first()
        cf = Customer.objects.filter(is_generic=True).first()
        vitrina_product = Product.objects.get(sku="VIT-002")  # 11 u @ $24.00 cost

        sale = create_sale(
            sale_date=date(2026, 11, 15),
            doc_type="FCF",
            customer=cf,
            payment_method=Sale.PaymentMethod.CASH,
            lines=[
                {
                    "line_type": "PRODUCT",
                    "product_id": vitrina_product.id,
                    "description": "Venta Mascarilla reconstructiva",
                    "quantity": "1.000",
                    "unit_price": "22.00",
                }
            ],
            user=user,
        )
        assert sale.journal_entry is not None
        assert Stock.objects.get(product=vitrina_product, location__code="VIT").quantity == Decimal("10.000")
        assert InventoryMovement.objects.filter(
            product=vitrina_product,
            source_app="sales.sale",
            movement_type=InventoryMovement.MovementType.SALE,
        ).exists()

    def test_inventory_and_purchases_api_endpoints(self):
        user = User.objects.filter(role=User.Role.ADMIN).first()
        client = APIClient()
        client.force_authenticate(user=user)

        inv_resp = client.get("/api/v1/inventory/summary/")
        assert inv_resp.status_code == 200
        assert len(inv_resp.data["vitrina_items"]) == 4
        assert len(inv_resp.data["cabina_items"]) == 4

        pb_resp = client.get("/api/v1/purchases/purchase-book/")
        assert pb_resp.status_code == 200
        assert pb_resp.data["kpis"]["documents_count"] == 3
