from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounting.exceptions import (
    ImmutableEntryError,
    InvalidAccountError,
    UnbalancedEntryError,
)
from apps.accounting.models import Account, AccountMapping, JournalEntry
from apps.accounting.services.posting import (
    LineDTO,
    create_draft_entry,
    get_account,
    post_draft_entry,
    post_entry,
    reverse_entry,
)
from apps.core.exceptions import ClosedPeriodError
from apps.core.models import AccountingPeriod, PeriodStatus, User


@pytest.mark.django_db
class TestChartOfAccountsAndPostingEngine:
    def test_seed_chart_mappings_and_entries(self):
        assert Account.objects.count() == 45
        assert AccountMapping.objects.count() == 17
        assert get_account("CASH").code == "110101"
        assert get_account("INVENTORY_VITRINA").code == "110501"
        assert get_account("INVENTORY_CABINA").code == "110502"
        assert get_account("IVA_DEBIT").code == "2107"
        assert get_account("INCOME_SERVICES").code == "5101"
        assert get_account("INCOME_PRODUCTS").code == "5102"

        # 7 initial November 2026 entries seeded
        nov = AccountingPeriod.objects.get(year=2026, month=11)
        assert JournalEntry.objects.filter(period=nov, status="POSTED").count() == 7

    def test_post_entry_and_unbalanced_rejection(self):
        accountant = User.objects.get(username="contador")

        # Valid balanced entry
        entry = post_entry(
            entry_date=date(2026, 11, 10),
            description="Venta FCF en efectivo de servicio de manicure",
            entry_type=JournalEntry.EntryType.SALE,
            lines=[
                LineDTO(account="CASH", debit=Decimal("25.00"), description="Cobro efectivo"),
                LineDTO(account="INCOME_SERVICES", credit=Decimal("22.12"), description="Servicio"),
                LineDTO(account="IVA_DEBIT", credit=Decimal("2.88"), description="IVA 13%"),
            ],
            source_app="sales.sale",
            source_id=99,
            user=accountant,
        )
        assert entry.status == JournalEntry.EntryStatus.POSTED
        assert entry.entry_number == 8
        assert entry.total_debit == Decimal("25.00")
        assert entry.total_credit == Decimal("25.00")

        # SRS Appendix A Scenario: Unbalanced manual entry cannot be posted ($10.00 vs $9.00)
        draft = create_draft_entry(
            entry_date=date(2026, 11, 10),
            description="Partida descuadrada de prueba",
            lines=[
                LineDTO(account="110101", debit=Decimal("10.00")),
                LineDTO(account="5101", credit=Decimal("9.00")),
            ],
            user=accountant,
        )
        with pytest.raises(UnbalancedEntryError) as exc_info:
            post_draft_entry(draft, user=accountant)
        assert "La partida no está cuadrada (diferencia $1.00)" in str(exc_info.value)

    def test_non_leaf_account_and_closed_period_rejected(self):
        accountant = User.objects.get(username="contador")
        admin = User.objects.get(username="admin")

        # Parent account 1101 does not accept entries (RN-04)
        with pytest.raises(InvalidAccountError):
            post_entry(
                entry_date=date(2026, 11, 10),
                description="Intento en cuenta mayor",
                entry_type=JournalEntry.EntryType.MANUAL,
                lines=[
                    LineDTO(account="1101", debit=Decimal("50.00")),
                    LineDTO(account="5101", credit=Decimal("50.00")),
                ],
                user=accountant,
            )

        # SRS Appendix A Scenario: Closed period is locked (October 2026)
        oct_period = AccountingPeriod.objects.get(year=2026, month=10)
        oct_period.status = PeriodStatus.CLOSED
        oct_period.closed_at = timezone.now()
        oct_period.closed_by = admin
        oct_period.save()

        with pytest.raises(ClosedPeriodError) as exc_closed:
            post_entry(
                entry_date=date(2026, 10, 15),
                description="Compra en período cerrado",
                entry_type=JournalEntry.EntryType.PURCHASE,
                lines=[
                    LineDTO(account="110501", debit=Decimal("100.00")),
                    LineDTO(account="110101", credit=Decimal("100.00")),
                ],
                user=accountant,
            )
        assert "El período 10/2026 está cerrado" in str(exc_closed.value)

    def test_reverse_entry_creates_mirror_and_marks_reversed(self):
        accountant = User.objects.get(username="contador")
        original = post_entry(
            entry_date=date(2026, 11, 12),
            description="Ajuste de caja por corregir",
            entry_type=JournalEntry.EntryType.MANUAL,
            lines=[
                LineDTO(account="420101", debit=Decimal("30.00"), description="Gasto general"),
                LineDTO(account="110101", credit=Decimal("30.00"), description="Salida de caja"),
            ],
            user=accountant,
        )

        reversal = reverse_entry(original, reason="Error en monto digitado", user=accountant)
        original.refresh_from_db()

        assert original.status == JournalEntry.EntryStatus.REVERSED
        assert reversal.status == JournalEntry.EntryStatus.POSTED
        assert reversal.entry_type == JournalEntry.EntryType.REVERSAL
        assert reversal.reversal_of_id == original.id
        assert reversal.total_debit == Decimal("30.00")
        assert reversal.total_credit == Decimal("30.00")

        rev_lines = list(reversal.lines.order_by("line_no"))
        assert rev_lines[0].account.code == "420101"
        assert rev_lines[0].credit == Decimal("30.00")
        assert rev_lines[1].account.code == "110101"
        assert rev_lines[1].debit == Decimal("30.00")

        # Cannot reverse twice
        with pytest.raises(ImmutableEntryError):
            reverse_entry(original, reason="Segundo intento", user=accountant)


@pytest.mark.django_db
class TestAccountingApiEndpoints:
    def setup_method(self):
        self.client = APIClient()
        self.accountant = User.objects.get(username="contador")
        self.client.force_authenticate(user=self.accountant)

    def test_accounts_tree_and_hierarchy_constraints(self):
        resp = self.client.get("/api/v1/accounts/?tree=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["is_balanced"] is True
        assert data["summary"]["class_counts"]["ALL"] == 45
        assert len(data["tree"]) == 5  # Classes 1, 2, 3, 4, 5

        # RF-CAT-04: Account 110101 has movements, so it cannot become a parent
        acc_caja = Account.objects.get(code="110101")
        bad_child = self.client.post(
            "/api/v1/accounts/",
            {
                "code": "11010101",
                "name": "Subcaja",
                "parent": acc_caja.id,
                "account_type": "ASSET",
                "nature": "DEBIT",
                "accepts_entries": True,
            },
            format="json",
        )
        assert bad_child.status_code == 400

        # RF-CAT-05: Cannot change code or nature of 110101 because it has movements
        locked_patch = self.client.patch(
            f"/api/v1/accounts/{acc_caja.id}/",
            {"nature": "CREDIT"},
            format="json",
        )
        assert locked_patch.status_code == 400

        # Create a valid new subaccount under 1101 Efectivo y equivalentes
        acc_1101 = Account.objects.get(code="1101")
        good_sub = self.client.post(
            "/api/v1/accounts/",
            {
                "code": "110103",
                "name": "Caja chica recepción",
                "parent": acc_1101.id,
                "account_type": "ASSET",
                "nature": "DEBIT",
                "classification": "Subcuenta analítica",
                "accepts_entries": True,
            },
            format="json",
        )
        assert good_sub.status_code == 201
        assert good_sub.json()["level"] == 4

    def test_journal_entry_crud_post_and_reverse_api(self):
        acc_gasto = Account.objects.get(code="420101")
        acc_caja = Account.objects.get(code="110101")

        # 1. Create as draft
        create_resp = self.client.post(
            "/api/v1/journal-entries/",
            {
                "entry_date": "2026-11-15",
                "description": "Pago de servicio de agua potable del salón",
                "entry_type": "MANUAL",
                "post_now": False,
                "lines": [
                    {"account": acc_gasto.id, "description": "Recibo ANDA", "debit": "18.75", "credit": "0.00"},
                    {"account": acc_caja.id, "description": "Efectivo caja", "debit": "0.00", "credit": "18.75"},
                ],
            },
            format="json",
        )
        assert create_resp.status_code == 201
        entry_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "DRAFT"

        # 2. Post the draft
        post_resp = self.client.post(f"/api/v1/journal-entries/{entry_id}/post/")
        assert post_resp.status_code == 200
        assert post_resp.json()["status"] == "POSTED"
        assert post_resp.json()["entry_number"] is not None

        # 3. Reverse the posted entry
        rev_resp = self.client.post(
            f"/api/v1/journal-entries/{entry_id}/reverse/",
            {"reason": "Recibo duplicado"},
            format="json",
        )
        assert rev_resp.status_code == 201
        assert rev_resp.json()["entry_type"] == "REVERSAL"
        assert rev_resp.json()["reversal_of"] == entry_id
