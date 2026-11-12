from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.exceptions import ClosedPeriodError
from apps.core.models import AccountingPeriod, AuditLog, Company, FiscalYear, PeriodStatus, User
from apps.core.services.periods import (
    activate_period,
    generate_fiscal_year_periods,
    generate_periods,
    get_active_period,
    get_open_period,
    period_usage,
    reopen_period,
    set_period_hidden,
)


@pytest.mark.django_db
class TestCoreSeedAndModels:
    def test_seed_company_and_periods_exist(self):
        company = Company.get_solo()
        assert company.id == 1
        assert company.trade_name == "Diamond Salón Atelier"
        assert company.iva_rate == Decimal("0.1300")

        fy = FiscalYear.objects.get(year=2026)
        assert fy.status == PeriodStatus.OPEN
        assert AccountingPeriod.objects.filter(fiscal_year=fy).count() == 12

        active = get_active_period()
        assert active is not None
        assert active.year == 2026
        assert active.month == 11
        assert active.label == "Noviembre 2026"

    def test_get_open_period_and_closed_period_error(self):
        # Open period returns period object
        nov = get_open_period(date(2026, 11, 15))
        assert nov.year == 2026
        assert nov.month == 11

        # Close October 2026 and verify SRS Appendix A scenario:
        # "El período 10/2026 está cerrado"
        admin = User.objects.get(username="admin")
        oct_period = AccountingPeriod.objects.get(year=2026, month=10)
        oct_period.status = PeriodStatus.CLOSED
        oct_period.closed_at = timezone.now()
        oct_period.closed_by = admin
        oct_period.save()

        with pytest.raises(ClosedPeriodError) as exc_info:
            get_open_period("2026-10-15")
        assert "El período 10/2026 está cerrado" in str(exc_info.value)

        # Reopen October 2026 with ADMIN and reason
        reopened = reopen_period(oct_period, user=admin, reason="Corrección de factura de compra")
        assert reopened.status == PeriodStatus.OPEN
        assert reopened.closed_at is None
        assert AuditLog.objects.filter(
            action=AuditLog.Action.REOPEN,
            table_name="core_accounting_period",
            record_id=oct_period.pk,
        ).exists()

    def test_generate_fiscal_year_periods(self):
        admin = User.objects.get(username="admin")
        fy_2027 = generate_fiscal_year_periods(2027, user=admin)
        assert fy_2027.year == 2027
        assert AccountingPeriod.objects.filter(year=2027).count() == 12

    def test_activate_period_switches_single_active(self):
        admin = User.objects.get(username="admin")
        dec = AccountingPeriod.objects.get(year=2026, month=12)
        activate_period(dec, user=admin)
        assert AccountingPeriod.objects.filter(is_active=True).count() == 1
        assert get_active_period().pk == dec.pk


@pytest.mark.django_db
class TestAuthRbacAndEndpoints:
    def setup_method(self):
        self.client = APIClient()

    def test_jwt_login_creates_audit_log_and_returns_user(self):
        resp = self.client.post(
            "/api/v1/auth/token/",
            {"username": "admin", "password": "diamond2026"},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access" in data
        assert "refresh" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "ADMIN"
        assert AuditLog.objects.filter(action="LOGIN", user__username="admin").exists()

    def test_rbac_user_management_and_company_settings(self):
        admin = User.objects.get(username="admin")
        cashier = User.objects.get(username="cajero")
        auditor = User.objects.get(username="auditor")

        # Cashier cannot list or create users
        self.client.force_authenticate(user=cashier)
        resp_forbidden = self.client.get("/api/v1/users/")
        assert resp_forbidden.status_code == 403

        # Cashier can read company settings, but cannot modify them
        assert self.client.get("/api/v1/company/").status_code == 200
        assert self.client.patch("/api/v1/company/", {"trade_name": "X"}, format="json").status_code == 403

        # Cashier cannot read audit log
        assert self.client.get("/api/v1/audit-log/").status_code == 403

        # Admin can create user and update company settings
        self.client.force_authenticate(user=admin)
        create_resp = self.client.post(
            "/api/v1/users/",
            {
                "username": "nuevo_contador",
                "password": "secretpassword123",
                "first_name": "Carlos",
                "last_name": "Pérez",
                "email": "carlos@diamondsalon.sv",
                "role": "ACCOUNTANT",
            },
            format="json",
        )
        assert create_resp.status_code == 201
        assert create_resp.json()["role"] == "ACCOUNTANT"

        patch_resp = self.client.patch(
            "/api/v1/company/",
            {"allow_negative_stock": True},
            format="json",
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["allow_negative_stock"] is True

        # Auditor can read audit log, but cannot mutate users
        self.client.force_authenticate(user=auditor)
        audit_resp = self.client.get("/api/v1/audit-log/")
        assert audit_resp.status_code == 200
        assert audit_resp.json()["count"] >= 2

    def test_dashboard_summary_search_and_notifications(self):
        admin = User.objects.get(username="admin")
        self.client.force_authenticate(user=admin)

        dash_resp = self.client.get("/api/v1/dashboard/summary/")
        assert dash_resp.status_code == 200
        dash = dash_resp.json()
        assert dash["period"]["label"] == "Noviembre 2026"
        assert "sales" in dash
        assert "purchases" in dash
        assert "tax" in dash
        assert "inventory" in dash

        search_resp = self.client.get("/api/v1/search/?q=ventas")
        assert search_resp.status_code == 200
        assert any(r["to"] == "/libro-ventas" for r in search_resp.json()["results"])

        notif_resp = self.client.get("/api/v1/notifications/")
        assert notif_resp.status_code == 200
        assert notif_resp.json()["count"] >= 1


@pytest.mark.django_db
class TestFlexiblePeriodManagement:
    """Partial / month-by-month generation, hide/show, and safe deletion of periods and years."""

    def setup_method(self):
        self.client = APIClient()
        self.admin = User.objects.get(username="admin")
        self.client.force_authenticate(user=self.admin)

    # -- Generation -----------------------------------------------------------------------

    def test_generate_full_year_is_backward_compatible(self):
        resp = self.client.post("/api/v1/periods/generate-year/", {"year": 2027}, format="json")
        assert resp.status_code == 201
        assert resp.json()["created_count"] == 12
        assert AccountingPeriod.objects.filter(year=2027).count() == 12

    def test_generate_month_range_then_specific_months_is_idempotent(self):
        resp = self.client.post(
            "/api/v1/periods/generate-year/",
            {"year": 2027, "mode": "RANGE", "start_month": 3, "end_month": 12},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["created_months"] == list(range(3, 13))
        assert AccountingPeriod.objects.filter(year=2027).count() == 10

        resp = self.client.post(
            "/api/v1/periods/generate-year/",
            {"year": 2027, "mode": "MONTHS", "months": [1, 2, 5]},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["created_months"] == [1, 2]
        assert AccountingPeriod.objects.filter(year=2027).count() == 12

    def test_generate_invalid_payloads(self):
        bad = [
            {"year": "abc"},
            {"year": 2027, "mode": "MONTHS", "months": [13]},
            {"year": 2027, "mode": "MONTHS", "months": []},
            {"year": 2027, "mode": "RANGE", "start_month": 8, "end_month": 3},
            {"year": 2027, "mode": "RANGE", "start_month": 3},
        ]
        for payload in bad:
            resp = self.client.post("/api/v1/periods/generate-year/", payload, format="json")
            assert resp.status_code == 400, payload
        assert not AccountingPeriod.objects.filter(year=2027).exists()

    def test_generate_next_rolls_over_into_new_fiscal_year(self):
        resp = self.client.post("/api/v1/periods/generate-next/")
        assert resp.status_code == 201
        assert (resp.json()["year"], resp.json()["month"]) == (2027, 1)
        assert FiscalYear.objects.filter(year=2027).exists()

        resp = self.client.post("/api/v1/periods/generate-next/")
        assert (resp.json()["year"], resp.json()["month"]) == (2027, 2)

    def test_generation_requires_admin(self):
        self.client.force_authenticate(user=User.objects.get(username="contador"))
        assert self.client.post("/api/v1/periods/generate-year/", {"year": 2027}, format="json").status_code == 403
        assert self.client.post("/api/v1/periods/generate-next/").status_code == 403

    # -- Visibility -----------------------------------------------------------------------

    def test_hide_and_show_period(self):
        jan = AccountingPeriod.objects.get(year=2026, month=1)
        assert self.client.post(f"/api/v1/periods/{jan.pk}/hide/").status_code == 200

        visible_ids = {p["id"] for p in self.client.get("/api/v1/periods/").json()}
        all_ids = {p["id"] for p in self.client.get("/api/v1/periods/?include_hidden=true").json()}
        assert jan.pk not in visible_ids
        assert jan.pk in all_ids

        assert self.client.post(f"/api/v1/periods/{jan.pk}/show/").status_code == 200
        assert jan.pk in {p["id"] for p in self.client.get("/api/v1/periods/").json()}

    def test_active_period_cannot_be_hidden_and_activation_unhides(self):
        nov = AccountingPeriod.objects.get(year=2026, month=11)
        resp = self.client.post(f"/api/v1/periods/{nov.pk}/hide/")
        assert resp.status_code == 400

        dec = AccountingPeriod.objects.get(year=2026, month=12)
        set_period_hidden(dec, True, user=self.admin)
        activate_period(dec, user=self.admin)
        dec.refresh_from_db()
        assert dec.is_active and not dec.is_hidden

    def test_hide_whole_fiscal_year_keeps_active_period_visible(self):
        fy = FiscalYear.objects.get(year=2026)
        resp = self.client.post(f"/api/v1/fiscal-years/{fy.pk}/hide/")
        assert resp.status_code == 200
        assert resp.json()["updated"] == 11
        assert not AccountingPeriod.objects.get(year=2026, month=11).is_hidden

    def test_cashier_cannot_hide(self):
        self.client.force_authenticate(user=User.objects.get(username="cajero"))
        jan = AccountingPeriod.objects.get(year=2026, month=1)
        assert self.client.post(f"/api/v1/periods/{jan.pk}/hide/").status_code == 403

    # -- Deletion -------------------------------------------------------------------------

    def test_delete_empty_period_is_audited(self):
        generate_periods(2027, [3, 4], user=self.admin)
        mar = AccountingPeriod.objects.get(year=2027, month=3)
        usage = self.client.get(f"/api/v1/periods/{mar.pk}/usage/").json()
        assert usage["can_delete"] is True

        resp = self.client.delete(f"/api/v1/periods/{mar.pk}/", {"reason": "Creado por error"}, format="json")
        assert resp.status_code == 200
        assert not AccountingPeriod.objects.filter(pk=mar.pk).exists()
        log = AuditLog.objects.get(action="DELETE", table_name="core_accounting_period", record_id=mar.pk)
        assert log.after_data["delete_reason"] == "Creado por error"

    def test_delete_period_with_data_or_closed_is_blocked(self):
        nov = AccountingPeriod.objects.get(year=2026, month=11)
        assert any(period_usage(nov).values()), "Seed data expected in Noviembre 2026"
        resp = self.client.delete(f"/api/v1/periods/{nov.pk}/")
        assert resp.status_code == 400
        assert "datos registrados" in resp.json()["detail"]

        generate_periods(2027, [1], user=self.admin)
        jan = AccountingPeriod.objects.get(year=2027, month=1)
        jan.status = PeriodStatus.CLOSED
        jan.closed_at = timezone.now()
        jan.save()
        assert self.client.delete(f"/api/v1/periods/{jan.pk}/").status_code == 400

    def test_delete_period_requires_admin(self):
        generate_periods(2027, [1], user=self.admin)
        jan = AccountingPeriod.objects.get(year=2027, month=1)
        self.client.force_authenticate(user=User.objects.get(username="contador"))
        assert self.client.delete(f"/api/v1/periods/{jan.pk}/").status_code == 403

    def test_delete_active_period_reassigns_active(self):
        generate_periods(2027, [3, 4, 5], user=self.admin)
        apr = AccountingPeriod.objects.get(year=2027, month=4)
        activate_period(apr, user=self.admin)

        resp = self.client.delete(f"/api/v1/periods/{apr.pk}/")
        assert resp.status_code == 200
        active = get_active_period()
        assert active is not None and active.is_active
        assert (active.year, active.month) in {(2027, 3), (2027, 5)}
        assert AccountingPeriod.objects.filter(is_active=True).count() == 1

    def test_deleting_last_month_removes_empty_fiscal_year(self):
        generate_periods(2028, [6], user=self.admin)
        jun = AccountingPeriod.objects.get(year=2028, month=6)
        resp = self.client.delete(f"/api/v1/periods/{jun.pk}/")
        assert resp.status_code == 200
        assert resp.json()["fiscal_year_deleted"] is True
        assert not FiscalYear.objects.filter(year=2028).exists()

    def test_delete_fiscal_year(self):
        generate_periods(2027, None, user=self.admin)
        fy_2027 = FiscalYear.objects.get(year=2027)
        listing = {fy["year"]: fy for fy in self.client.get("/api/v1/fiscal-years/").json()}
        assert listing[2027]["can_delete"] is True
        assert listing[2027]["periods_count"] == 12
        assert listing[2026]["can_delete"] is False

        resp = self.client.delete(f"/api/v1/fiscal-years/{fy_2027.pk}/")
        assert resp.status_code == 200
        assert resp.json()["deleted_periods"] == 12
        assert not FiscalYear.objects.filter(year=2027).exists()
        assert not AccountingPeriod.objects.filter(year=2027).exists()

        fy_2026 = FiscalYear.objects.get(year=2026)
        resp = self.client.delete(f"/api/v1/fiscal-years/{fy_2026.pk}/")
        assert resp.status_code == 400
        assert "Noviembre" in resp.json()["detail"]
        assert AccountingPeriod.objects.filter(year=2026).count() == 12
