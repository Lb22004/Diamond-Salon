from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounting.models import JournalEntry
from apps.core.models import AccountingPeriod, User
from apps.sales.models import Customer, Sale, Service
from apps.sales.services import (
    compute_iva_withholding,
    create_sale,
    get_sales_book,
    split_iva,
    void_sale,
)


@pytest.mark.django_db
class TestTaxAndSalesEngine:
    def test_split_iva_and_withholding_precision(self):
        # FCF prices include 13% IVA (RN-06, RF-VEN-03)
        taxable_25, iva_25 = split_iva(Decimal("25.00"), price_includes_iva=True)
        assert taxable_25 == Decimal("22.12")
        assert iva_25 == Decimal("2.88")
        assert taxable_25 + iva_25 == Decimal("25.00")

        taxable_12, iva_12 = split_iva(Decimal("12.00"), price_includes_iva=True)
        assert taxable_12 == Decimal("10.62")
        assert iva_12 == Decimal("1.38")
        assert taxable_12 + iva_12 == Decimal("12.00")

        # CCF prices exclude 13% IVA
        taxable_100, iva_100 = split_iva(Decimal("100.00"), price_includes_iva=False)
        assert taxable_100 == Decimal("100.00")
        assert iva_100 == Decimal("13.00")

        # 1% IVA withholding for large taxpayer on CCF
        wh = compute_iva_withholding(Decimal("100.00"), is_large_taxpayer=True, doc_type="CCF")
        assert wh == Decimal("1.00")
        assert compute_iva_withholding(Decimal("100.00"), is_large_taxpayer=True, doc_type="FCF") == Decimal("0.00")

    def test_seeded_nov_2026_sales_book(self):
        nov = AccountingPeriod.objects.get(year=2026, month=11)
        book = get_sales_book(period=nov)

        assert book["kpis"]["gross_sales"] == "70.00"
        assert book["kpis"]["taxable_base"] == "61.94"
        assert book["kpis"]["iva_debit"] == "8.06"
        assert book["kpis"]["documents_issued"] == 4
        assert book["regime_summary"]["cabina"]["amount"] == "40.00"
        assert book["regime_summary"]["vitrina"]["amount"] == "30.00"
        assert book["totals"]["is_verified"] is True

    def test_ccf_requires_taxpayer_and_creates_automatic_entries(self):
        cajero = User.objects.get(username="cajero")
        cf = Customer.objects.filter(is_generic=True).first()
        large_tp = Customer.objects.get(nrc="190422-8")
        srv = Service.objects.get(code="SRV-001")

        # RF-VEN-04: CCF for Final Consumer must fail
        with pytest.raises(ValidationError):
            create_sale(
                sale_date=date(2026, 11, 10),
                doc_type="CCF",
                customer=cf,
                payment_method="CASH",
                lines=[{"line_type": "SERVICE", "service_id": srv.id, "quantity": 1, "unit_price": "100.00"}],
                user=cajero,
            )

        # Valid CCF for Large Taxpayer (1% IVA withheld)
        ccf_sale = create_sale(
            sale_date=date(2026, 11, 10),
            doc_type="CCF",
            customer=large_tp,
            payment_method="CREDIT",
            lines=[{"line_type": "SERVICE", "service_id": srv.id, "quantity": 1, "unit_price": "100.00"}],
            user=cajero,
        )
        assert ccf_sale.doc_number == "CCF-0001"
        assert ccf_sale.taxable_amount == Decimal("100.00")
        assert ccf_sale.iva_amount == Decimal("13.00")
        assert ccf_sale.iva_withheld == Decimal("1.00")
        assert ccf_sale.total == Decimal("112.00")
        assert ccf_sale.journal_entry is not None
        assert ccf_sale.journal_entry.status == JournalEntry.EntryStatus.POSTED
        assert ccf_sale.journal_entry.total_debit == Decimal("113.00")
        assert ccf_sale.journal_entry.total_credit == Decimal("113.00")

        # Product FCF sale generates income, IVA, and cost of sales lines (Gherkin Scenario 1)
        fcf_sale = create_sale(
            sale_date=date(2026, 11, 11),
            doc_type="FCF",
            customer=cf,
            payment_method="CASH",
            lines=[
                {
                    "line_type": "PRODUCT",
                    "product_id": 1,
                    "description": "Champú nutritivo 300ml",
                    "quantity": 1,
                    "unit_price": "12.00",
                    "unit_cost": "7.0000",
                }
            ],
            user=cajero,
        )
        assert fcf_sale.doc_number == "FCF-0016"
        assert fcf_sale.taxable_amount == Decimal("10.62")
        assert fcf_sale.iva_amount == Decimal("1.38")
        assert fcf_sale.total == Decimal("12.00")
        # Total debit = 12.00 (Caja) + 7.00 (Costo de venta) = 19.00
        assert fcf_sale.journal_entry.total_debit == Decimal("19.00")
        assert fcf_sale.journal_entry.total_credit == Decimal("19.00")

        # Voiding the sale reverses its journal entry (RF-VEN-10)
        voided = void_sale(fcf_sale, reason="Error de digitación en caja", user=cajero)
        assert voided.status == Sale.SaleStatus.VOIDED
        voided.journal_entry.refresh_from_db()
        assert voided.journal_entry.status == JournalEntry.EntryStatus.REVERSED


@pytest.mark.django_db
class TestSalesApiEndpoints:
    def test_sales_book_create_and_export_api(self):
        client = APIClient()
        cajero = User.objects.get(username="cajero")
        client.force_authenticate(user=cajero)

        res_book = client.get("/api/v1/sales-book/")
        assert res_book.status_code == 200
        assert res_book.data["kpis"]["gross_sales"] == "70.00"

        cf = Customer.objects.filter(is_generic=True).first()
        srv = Service.objects.get(code="SRV-004")

        res_post = client.post(
            "/api/v1/sales/",
            {
                "sale_date": "2026-11-12",
                "doc_type": "FCF",
                "customer": cf.id,
                "payment_method": "CARD",
                "lines": [
                    {
                        "line_type": "SERVICE",
                        "service_id": srv.id,
                        "quantity": 1,
                        "unit_price": "20.00",
                    }
                ],
            },
            format="json",
        )
        assert res_post.status_code == 201
        assert res_post.data["doc_number"] == "FCF-0016"

        res_export = client.get("/api/v1/exports/sales/?format=pdf")
        assert res_export.status_code == 200
        assert res_export.content.startswith(b"%PDF")
