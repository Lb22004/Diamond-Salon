from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounting.models import JournalEntry, PeriodBalance
from apps.accounting.services.posting import LineDTO, create_draft_entry, post_entry
from apps.core.exceptions import ClosedPeriodError
from apps.core.models import AccountingPeriod, AuditLog, PeriodStatus, User
from apps.reports.services import (
    close_period,
    get_account_ledger,
    get_close_preview,
    get_financial_statements,
    get_trial_balance,
)


@pytest.mark.django_db
class TestGeneralLedgerAndStatements:
    def test_account_ledger_caja_general_nov_2026(self):
        nov = AccountingPeriod.objects.get(year=2026, month=11)
        data = get_account_ledger(account_identifier="110101", period=nov)

        assert data["account"]["code"] == "110101"
        assert data["kpis"]["opening_balance"] == "0.00"
        assert data["kpis"]["effective_initial_balance"] == "1850.00"
        assert data["kpis"]["debit_total"] == "1887.00"
        assert data["kpis"]["credit_total"] == "101.70"
        assert data["kpis"]["closing_balance"] == "1785.30"
        assert data["verification"]["trial_balance_ok"] is True
        assert len(data["movements"]) == 4
        assert data["movements"][-1]["resulting_balance"] == "1785.30"
        assert len(data["simultaneous_summary"]) >= 7

    def test_trial_balance_and_financial_statements_are_balanced(self):
        nov = AccountingPeriod.objects.get(year=2026, month=11)
        tb = get_trial_balance(period=nov)
        assert tb["totals"]["is_balanced"] is True
        assert Decimal(tb["totals"]["debit_total"]) == Decimal(tb["totals"]["credit_total"])
        assert Decimal(tb["totals"]["closing_debit"]) == Decimal(tb["totals"]["closing_credit"])

        fs = get_financial_statements(period=nov)
        assert fs["balance_sheet"]["is_balanced"] is True
        assert Decimal(fs["balance_sheet"]["total_assets"]) == Decimal(
            fs["balance_sheet"]["total_liabilities_and_equity"]
        )


@pytest.mark.django_db
class TestMonthlyClosingWorkflow:
    def test_close_preview_blocks_when_draft_exists(self):
        nov = AccountingPeriod.objects.get(year=2026, month=11)
        admin = User.objects.get(username="admin")

        draft = create_draft_entry(
            entry_date=date(2026, 11, 20),
            description="Borrador pendiente antes de cierre",
            lines=[
                LineDTO(account="110101", debit=Decimal("10.00"), credit=Decimal("0.00")),
                LineDTO(account="510101", debit=Decimal("0.00"), credit=Decimal("10.00")),
            ],
            user=admin,
        )

        preview = get_close_preview(nov)
        assert preview["can_close"] is False
        draft_check = next(c for c in preview["checks"] if c["key"] == "no_draft_entries")
        assert draft_check["ok"] is False

        # Clean up draft and verify preview turns green
        draft.delete()
        preview_after = get_close_preview(nov)
        assert preview_after["can_close"] is True
        assert preview_after["iva_liquidation"]["iva_debit"] == "4.26"
        assert preview_after["iva_liquidation"]["iva_credit"] == "31.20"
        assert preview_after["iva_liquidation"]["credit_remainder"] == "26.94"

    def test_execute_period_close_liquidates_iva_snapshots_and_locks(self):
        nov = AccountingPeriod.objects.get(year=2026, month=11)
        contador = User.objects.get(username="contador")

        result = close_period(nov, user=contador, post_iva_liquidation=True)
        nov.refresh_from_db()

        assert nov.status == PeriodStatus.CLOSED
        assert nov.closed_by == contador
        assert result["snapshots_count"] > 0
        assert result["liquidation_entry"] is not None
        assert result["liquidation_entry"]["entry_type"] == JournalEntry.EntryType.CLOSING

        # Verify PeriodBalance snapshot for 110101 Caja general = 1785.30
        pb_caja = PeriodBalance.objects.get(period=nov, account__code="110101")
        assert pb_caja.closing_balance == Decimal("1785.30")

        # Verify PeriodBalance snapshot for 210201 IVA débito is now 0.00 after liquidation
        pb_iva_deb = PeriodBalance.objects.get(period=nov, account__code="210201")
        assert pb_iva_deb.closing_balance == Decimal("0.00")

        # Verify posting into the closed period is rejected
        with pytest.raises(ClosedPeriodError):
            post_entry(
                entry_date=date(2026, 11, 25),
                description="Intento en período cerrado",
                entry_type=JournalEntry.EntryType.MANUAL,
                lines=[
                    LineDTO(account="110101", debit=Decimal("5.00"), credit=Decimal("0.00")),
                    LineDTO(account="510101", debit=Decimal("0.00"), credit=Decimal("5.00")),
                ],
                user=contador,
            )


@pytest.mark.django_db
class TestReportsAndExportsAPI:
    def test_ledger_and_export_endpoints(self):
        client = APIClient()
        contador = User.objects.get(username="contador")
        client.force_authenticate(user=contador)

        res_ledger = client.get("/api/v1/ledger/?account=110101")
        assert res_ledger.status_code == 200
        assert res_ledger.data["kpis"]["closing_balance"] == "1785.30"

        res_pdf = client.get("/api/v1/exports/ledger/?format=pdf&account=110101")
        assert res_pdf.status_code == 200
        assert res_pdf["Content-Type"] == "application/pdf"
        assert res_pdf.content.startswith(b"%PDF")

        res_xlsx = client.get("/api/v1/exports/trial-balance/?format=xlsx")
        assert res_xlsx.status_code == 200
        assert (
            res_xlsx["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert res_xlsx.content.startswith(b"PK")

        assert AuditLog.objects.filter(action=AuditLog.Action.EXPORT).count() >= 2
