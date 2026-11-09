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
    get_active_period,
    get_open_period,
    reopen_period,
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
