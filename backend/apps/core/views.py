from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection
from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.models import AccountingPeriod, AuditLog, Company, Employee, FiscalYear, PeriodStatus, User
from apps.core.permissions import (
    CanViewAuditLog,
    IsAccountantOrAdmin,
    IsAdminOrReadOnly,
    IsAdminRole,
)
from apps.core.serializers import (
    AccountingPeriodSerializer,
    AuditLogSerializer,
    CompanySerializer,
    CustomTokenObtainPairSerializer,
    EmployeeSerializer,
    FiscalYearSerializer,
    UserSerializer,
)
from apps.core.services.audit import log_audit, serialize_instance
from apps.core.services.periods import (
    activate_period,
    generate_fiscal_year_periods,
    get_active_period,
    reopen_period,
)


def health(request):
    """Public liveness/readiness probe used by the frontend shell and Docker."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()[0].split(" on ")[0]
        return JsonResponse({"status": "ok", "database": db_version})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"status": "error", "detail": str(exc)}, status=503)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class MeView(APIView):
    """Returns the authenticated user profile, company settings, and active period."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = Company.get_solo()
        active_period = get_active_period()
        return Response(
            {
                "user": UserSerializer(request.user).data,
                "company": CompanySerializer(company).data,
                "active_period": AccountingPeriodSerializer(active_period).data if active_period else None,
            }
        )


class UserViewSet(viewsets.ModelViewSet):
    """Admin CRUD for system users and role assignments (RF-SEG-04)."""

    queryset = User.objects.all().order_by("username")
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "first_name", "last_name", "email"]
    ordering_fields = ["username", "role", "date_joined"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            action=AuditLog.Action.CREATE,
            table_name="core_user",
            record_id=instance.pk,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )

    def perform_update(self, serializer):
        before = serialize_instance(serializer.instance)
        instance = serializer.save()
        log_audit(
            action=AuditLog.Action.UPDATE,
            table_name="core_user",
            record_id=instance.pk,
            before_data=before,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )

    def perform_destroy(self, instance):
        # Soft-deactivate rather than hard delete to preserve foreign key audit history
        before = serialize_instance(instance)
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        log_audit(
            action=AuditLog.Action.DELETE,
            table_name="core_user",
            record_id=instance.pk,
            before_data=before,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )


class CompanyView(APIView):
    """Single-tenant company configuration endpoint (RF-SEG-05)."""

    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        company = Company.get_solo()
        return Response(CompanySerializer(company).data)

    def put(self, request):
        return self._update(request, partial=False)

    def patch(self, request):
        return self._update(request, partial=True)

    def _update(self, request, partial: bool):
        company = Company.get_solo()
        before = serialize_instance(company)
        serializer = CompanySerializer(company, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        log_audit(
            action=AuditLog.Action.UPDATE,
            table_name="core_company",
            record_id=instance.pk,
            before_data=before,
            after_data=serialize_instance(instance),
            user=request.user,
        )
        return Response(CompanySerializer(instance).data)


class EmployeeViewSet(viewsets.ModelViewSet):
    """CRUD for salon stylists, manicurists, and staff."""

    queryset = Employee.objects.all().order_by("full_name")
    serializer_class = EmployeeSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["position", "is_active"]
    search_fields = ["full_name"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            action=AuditLog.Action.CREATE,
            table_name="core_employee",
            record_id=instance.pk,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )

    def perform_update(self, serializer):
        before = serialize_instance(serializer.instance)
        instance = serializer.save()
        log_audit(
            action=AuditLog.Action.UPDATE,
            table_name="core_employee",
            record_id=instance.pk,
            before_data=before,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )


class FiscalYearViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FiscalYear.objects.all().order_by("-year")
    serializer_class = FiscalYearSerializer
    permission_classes = [IsAuthenticated]


class AccountingPeriodViewSet(viewsets.ReadOnlyModelViewSet):
    """Accounting period selector & lifecycle endpoints (RF-GEN-01, RF-CIE-01, RF-CIE-05)."""

    queryset = AccountingPeriod.objects.select_related("fiscal_year", "closed_by").order_by("-year", "-month")
    serializer_class = AccountingPeriodSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["year", "month", "status", "is_active"]

    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        period = get_active_period()
        if not period:
            return Response({"detail": "No hay período activo configurado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(period).data)

    @action(
        detail=False,
        methods=["post"],
        url_path="generate-year",
        permission_classes=[IsAdminRole],
    )
    def generate_year(self, request):
        year = request.data.get("year")
        try:
            year_int = int(year)
            fy = generate_fiscal_year_periods(year_int, user=request.user)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Debe indicar un año numérico válido (ej. 2026)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)

        periods = AccountingPeriod.objects.filter(fiscal_year=fy).order_by("month")
        return Response(
            {
                "fiscal_year": FiscalYearSerializer(fy).data,
                "periods": AccountingPeriodSerializer(periods, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="activate",
        permission_classes=[IsAccountantOrAdmin],
    )
    def activate(self, request, pk=None):
        period = self.get_object()
        updated = activate_period(period, user=request.user)
        return Response(self.get_serializer(updated).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="reopen",
        permission_classes=[IsAdminRole],
    )
    def reopen(self, request, pk=None):
        period = self.get_object()
        reason = request.data.get("reason", "")
        try:
            reopened = reopen_period(period, user=request.user, reason=reason)
        except DjangoValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(reopened).data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Append-only audit trail query endpoint (RF-SEG-03, RNF-05)."""

    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    permission_classes = [CanViewAuditLog]
    filterset_fields = ["action", "table_name", "user"]
    search_fields = ["table_name", "user__username", "action"]
    ordering_fields = ["created_at", "id"]


def _existing_tables() -> set[str]:
    return set(connection.introspection.table_names())


class DashboardSummaryView(APIView):
    """Live KPI aggregation for the Panel (Dashboard) view (RF-PAN-01)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_id = request.query_params.get("period")
        period = None
        if period_id:
            period = AccountingPeriod.objects.filter(pk=period_id).first()
        if period is None:
            period = get_active_period()

        company = Company.get_solo()
        tables = _existing_tables()

        sales_data = {
            "total": "0.00",
            "taxable": "0.00",
            "iva_debit": "0.00",
            "services_total": "0.00",
            "products_total": "0.00",
            "services_count": 0,
            "products_count": 0,
            "documents_count": 0,
        }
        purchases_data = {
            "total": "0.00",
            "taxable": "0.00",
            "iva_credit": "0.00",
            "vitrina_total": "0.00",
            "cabina_total": "0.00",
            "documents_count": 0,
        }
        cash_balance = Decimal("0.00")
        vitrina_value = Decimal("0.00")
        cabina_value = Decimal("0.00")
        critical_stock_items = []
        posted_count = 0
        draft_count = 0
        recent_entries = []

        with connection.cursor() as cursor:
            # 1. Sales KPIs if sales_sale exists
            if period and "sales_sale" in tables:
                cursor.execute(
                    """
                    SELECT
                        COALESCE(SUM(total), 0),
                        COALESCE(SUM(taxable_amount), 0),
                        COALESCE(SUM(iva_amount), 0),
                        COUNT(*)
                    FROM sales_sale
                    WHERE status = 'ISSUED'
                      AND sale_date BETWEEN %s AND %s
                    """,
                    [period.start_date, period.end_date],
                )
                row = cursor.fetchone()
                if row:
                    sales_data["total"] = f"{Decimal(row[0]):.2f}"
                    sales_data["taxable"] = f"{Decimal(row[1]):.2f}"
                    sales_data["iva_debit"] = f"{Decimal(row[2]):.2f}"
                    sales_data["documents_count"] = int(row[3])

                if "sales_sale_line" in tables:
                    cursor.execute(
                        """
                        SELECT
                            l.line_type,
                            COALESCE(SUM(l.total), 0),
                            COUNT(DISTINCT s.id)
                        FROM sales_sale_line l
                        JOIN sales_sale s ON s.id = l.sale_id
                        WHERE s.status = 'ISSUED'
                          AND s.sale_date BETWEEN %s AND %s
                        GROUP BY l.line_type
                        """,
                        [period.start_date, period.end_date],
                    )
                    for line_type, line_sum, doc_cnt in cursor.fetchall():
                        if line_type == "SERVICE":
                            sales_data["services_total"] = f"{Decimal(line_sum):.2f}"
                            sales_data["services_count"] = int(doc_cnt)
                        elif line_type == "PRODUCT":
                            sales_data["products_total"] = f"{Decimal(line_sum):.2f}"
                            sales_data["products_count"] = int(doc_cnt)

            # 2. Purchases KPIs if purchases_purchase exists
            if period and "purchases_purchase" in tables:
                cursor.execute(
                    """
                    SELECT
                        COALESCE(SUM(total), 0),
                        COALESCE(SUM(taxable_amount), 0),
                        COALESCE(SUM(iva_credit), 0),
                        COALESCE(SUM(CASE WHEN destination = 'VITRINA' THEN total ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN destination = 'CABINA' THEN total ELSE 0 END), 0),
                        COUNT(*)
                    FROM purchases_purchase
                    WHERE status = 'POSTED'
                      AND purchase_date BETWEEN %s AND %s
                    """,
                    [period.start_date, period.end_date],
                )
                row = cursor.fetchone()
                if row:
                    purchases_data["total"] = f"{Decimal(row[0]):.2f}"
                    purchases_data["taxable"] = f"{Decimal(row[1]):.2f}"
                    purchases_data["iva_credit"] = f"{Decimal(row[2]):.2f}"
                    purchases_data["vitrina_total"] = f"{Decimal(row[3]):.2f}"
                    purchases_data["cabina_total"] = f"{Decimal(row[4]):.2f}"
                    purchases_data["documents_count"] = int(row[5])

            # 3. Journal & Ledger KPIs if accounting_journal_entry exists
            if "accounting_journal_entry" in tables and "accounting_account" in tables:
                if period:
                    cursor.execute(
                        """
                        SELECT
                            COUNT(*) FILTER (WHERE status IN ('POSTED', 'REVERSED')),
                            COUNT(*) FILTER (WHERE status = 'DRAFT')
                        FROM accounting_journal_entry
                        WHERE period_id = %s
                        """,
                        [period.pk],
                    )
                    j_row = cursor.fetchone()
                    if j_row:
                        posted_count = int(j_row[0] or 0)
                        draft_count = int(j_row[1] or 0)

                    cursor.execute(
                        """
                        SELECT id, entry_number, entry_date, description, entry_type, status, total_debit
                        FROM accounting_journal_entry
                        WHERE period_id = %s
                        ORDER BY entry_date DESC, entry_number DESC NULLS LAST, id DESC
                        LIMIT 6
                        """,
                        [period.pk],
                    )
                    for r in cursor.fetchall():
                        recent_entries.append(
                            {
                                "id": r[0],
                                "entry_number": r[1],
                                "entry_date": r[2].isoformat() if r[2] else None,
                                "description": r[3],
                                "entry_type": r[4],
                                "status": r[5],
                                "total": f"{Decimal(r[6] or 0):.2f}",
                            }
                        )

                if "accounting_journal_entry_line" in tables:
                    date_cutoff = period.end_date if period else date.today()
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(l.debit - l.credit), 0)
                        FROM accounting_journal_entry_line l
                        JOIN accounting_journal_entry e ON e.id = l.entry_id
                        JOIN accounting_account a ON a.id = l.account_id
                        WHERE a.code LIKE '1101%%'
                          AND e.status IN ('POSTED', 'REVERSED')
                          AND e.entry_date <= %s
                        """,
                        [date_cutoff],
                    )
                    c_row = cursor.fetchone()
                    if c_row and c_row[0] is not None:
                        cash_balance = Decimal(c_row[0])

            # 4. Inventory valuation & critical stock if inventory_product exists
            if "inventory_product" in tables and "inventory_stock" in tables:
                cursor.execute(
                    """
                    SELECT
                        p.inventory_type,
                        COALESCE(SUM(s.quantity * p.average_cost), 0)
                    FROM inventory_product p
                    LEFT JOIN inventory_stock s ON s.product_id = p.id
                    WHERE p.is_active = true
                    GROUP BY p.inventory_type
                    """
                )
                for inv_type, val in cursor.fetchall():
                    if inv_type == "VITRINA":
                        vitrina_value = Decimal(val or 0)
                    elif inv_type == "CABINA":
                        cabina_value = Decimal(val or 0)

                cursor.execute(
                    """
                    SELECT
                        p.id,
                        p.sku,
                        p.name,
                        p.inventory_type,
                        COALESCE(SUM(s.quantity), 0) AS current_qty,
                        p.min_stock
                    FROM inventory_product p
                    LEFT JOIN inventory_stock s ON s.product_id = p.id
                    WHERE p.is_active = true
                    GROUP BY p.id, p.sku, p.name, p.inventory_type, p.min_stock
                    HAVING COALESCE(SUM(s.quantity), 0) <= p.min_stock
                    ORDER BY COALESCE(SUM(s.quantity), 0) ASC
                    LIMIT 10
                    """
                )
                for r in cursor.fetchall():
                    critical_stock_items.append(
                        {
                            "id": r[0],
                            "sku": r[1],
                            "name": r[2],
                            "inventory_type": r[3],
                            "quantity": f"{Decimal(r[4] or 0):.2f}",
                            "min_stock": f"{Decimal(r[5] or 0):.2f}",
                        }
                    )

        iva_debit_dec = Decimal(sales_data["iva_debit"])
        iva_credit_dec = Decimal(purchases_data["iva_credit"])
        iva_net_payable = max(Decimal("0.00"), iva_debit_dec - iva_credit_dec)
        iva_credit_remainder = max(Decimal("0.00"), iva_credit_dec - iva_debit_dec)

        return Response(
            {
                "period": AccountingPeriodSerializer(period).data if period else None,
                "company": CompanySerializer(company).data,
                "sales": sales_data,
                "purchases": purchases_data,
                "tax": {
                    "iva_debit": f"{iva_debit_dec:.2f}",
                    "iva_credit": f"{iva_credit_dec:.2f}",
                    "iva_net_payable": f"{iva_net_payable:.2f}",
                    "iva_credit_remainder": f"{iva_credit_remainder:.2f}",
                },
                "cash_balance": f"{cash_balance:.2f}",
                "inventory": {
                    "vitrina_value": f"{vitrina_value:.2f}",
                    "cabina_value": f"{cabina_value:.2f}",
                    "critical_stock_count": len(critical_stock_items),
                    "critical_stock_items": critical_stock_items,
                },
                "journal": {
                    "posted_count": posted_count,
                    "draft_count": draft_count,
                    "recent_entries": recent_entries,
                },
            }
        )


class GlobalSearchView(APIView):
    """Global command palette search (`Ctrl+K`) across views, accounts, entries, and documents (RF-GEN-02)."""

    permission_classes = [IsAuthenticated]

    STATIC_VIEWS = [
        {"title": "Panel Principal (Dashboard)", "subtitle": "KPIs y resumen del período", "to": "/panel", "category": "VISTA"},
        {"title": "Catálogo de cuentas", "subtitle": "Vista 1 · Plan de cuentas NIIF PYMES", "to": "/catalogo-cuentas", "category": "VISTA"},
        {"title": "Inventario mixto", "subtitle": "Vista 2 · Vitrina (Venta) y Cabina (Insumos)", "to": "/inventario", "category": "VISTA"},
        {"title": "Libro de ventas", "subtitle": "Vista 3 · Facturación FCF y CCF", "to": "/libro-ventas", "category": "VISTA"},
        {"title": "Libro de compras", "subtitle": "Vista 4 · Compras CCF y proveedores", "to": "/libro-compras", "category": "VISTA"},
        {"title": "Libro diario", "subtitle": "Vista 5 · Partidas contables y asientos manuales", "to": "/libro-diario", "category": "VISTA"},
        {"title": "Libro mayor", "subtitle": "Vista 6 · Mayorización, saldos y cierre mensual", "to": "/libro-mayor", "category": "VISTA"},
        {"title": "Usuarios y Roles", "subtitle": "Administración de accesos RBAC", "to": "/usuarios", "category": "ADMIN"},
        {"title": "Configuración y Períodos", "subtitle": "Datos de empresa, IVA, períodos y bitácora", "to": "/configuracion", "category": "ADMIN"},
    ]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        results = []

        q_lower = q.lower()
        for item in self.STATIC_VIEWS:
            if not q or q_lower in item["title"].lower() or q_lower in item["subtitle"].lower():
                results.append(item)

        if len(q) >= 1:
            tables = _existing_tables()
            like_pattern = f"%{q}%"
            with connection.cursor() as cursor:
                if "accounting_account" in tables:
                    cursor.execute(
                        """
                        SELECT code, name, classification
                        FROM accounting_account
                        WHERE LOWER(code) LIKE LOWER(%s) OR LOWER(name) LIKE LOWER(%s)
                        ORDER BY code ASC
                        LIMIT 6
                        """,
                        [like_pattern, like_pattern],
                    )
                    for code, name, classification in cursor.fetchall():
                        results.append(
                            {
                                "title": f"{code} · {name}",
                                "subtitle": classification or "Cuenta contable",
                                "to": f"/catalogo-cuentas?q={code}",
                                "category": "CUENTA",
                            }
                        )

                if "accounting_journal_entry" in tables:
                    cursor.execute(
                        """
                        SELECT id, entry_number, entry_date, description
                        FROM accounting_journal_entry
                        WHERE LOWER(CAST(entry_number AS TEXT)) LIKE LOWER(%s)
                           OR LOWER(description) LIKE LOWER(%s)
                        ORDER BY entry_date DESC, id DESC
                        LIMIT 5
                        """,
                        [like_pattern, like_pattern],
                    )
                    for entry_id, entry_no, entry_date, desc in cursor.fetchall():
                        label_no = f"Partida N.º {entry_no}" if entry_no else f"Borrador #{entry_id}"
                        results.append(
                            {
                                "title": f"{label_no} ({entry_date})",
                                "subtitle": desc[:80],
                                "to": f"/libro-diario?entry={entry_id}",
                                "category": "PARTIDA",
                            }
                        )

                if "sales_sale" in tables:
                    cursor.execute(
                        """
                        SELECT id, doc_type, doc_number, sale_date, total
                        FROM sales_sale
                        WHERE LOWER(doc_number) LIKE LOWER(%s)
                        ORDER BY sale_date DESC
                        LIMIT 5
                        """,
                        [like_pattern],
                    )
                    for sale_id, doc_type, doc_num, sale_date, total in cursor.fetchall():
                        results.append(
                            {
                                "title": f"Venta {doc_type} {doc_num}",
                                "subtitle": f"Fecha {sale_date} · Total ${Decimal(total):.2f}",
                                "to": f"/libro-ventas?doc={doc_num}",
                                "category": "DOCUMENTO",
                            }
                        )

                if "purchases_purchase" in tables:
                    cursor.execute(
                        """
                        SELECT id, doc_type, doc_number, purchase_date, total
                        FROM purchases_purchase
                        WHERE LOWER(doc_number) LIKE LOWER(%s)
                        ORDER BY purchase_date DESC
                        LIMIT 5
                        """,
                        [like_pattern],
                    )
                    for pur_id, doc_type, doc_num, pur_date, total in cursor.fetchall():
                        results.append(
                            {
                                "title": f"Compra {doc_type} {doc_num}",
                                "subtitle": f"Fecha {pur_date} · Total ${Decimal(total):.2f}",
                                "to": f"/libro-compras?doc={doc_num}",
                                "category": "DOCUMENTO",
                            }
                        )

        return Response({"query": q, "results": results[:20]})


class NotificationsView(APIView):
    """Notification bell feed for critical stock, periods pending close, and draft entries (RF-GEN-05)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = []
        active_period = get_active_period()

        # 1. Prior open periods before the active period
        if active_period:
            prior_open_count = (
                AccountingPeriod.objects.filter(status=PeriodStatus.OPEN)
                .filter(start_date__lt=active_period.start_date)
                .count()
            )
            if prior_open_count > 0:
                notifications.append(
                    {
                        "id": "open-periods",
                        "level": "warning",
                        "title": f"{prior_open_count} período(s) anteriores abiertos",
                        "detail": "Existen meses previos a Noviembre 2026 pendientes de cierre contable.",
                        "to": "/libro-mayor",
                    }
                )

        tables = _existing_tables()
        with connection.cursor() as cursor:
            # 2. Critical stock alerts
            if "inventory_product" in tables and "inventory_stock" in tables:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM (
                        SELECT p.id
                        FROM inventory_product p
                        LEFT JOIN inventory_stock s ON s.product_id = p.id
                        WHERE p.is_active = true
                        GROUP BY p.id, p.min_stock
                        HAVING COALESCE(SUM(s.quantity), 0) <= p.min_stock
                    ) AS crit
                    """
                )
                crit_count = int(cursor.fetchone()[0] or 0)
                if crit_count > 0:
                    notifications.append(
                        {
                            "id": "critical-stock",
                            "level": "danger",
                            "title": f"{crit_count} producto(s) en stock crítico",
                            "detail": "Existencias iguales o por debajo del stock mínimo configurado.",
                            "to": "/inventario",
                        }
                    )

            # 3. Draft journal entries pending posting
            if active_period and "accounting_journal_entry" in tables:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM accounting_journal_entry
                    WHERE period_id = %s AND status = 'DRAFT'
                    """,
                    [active_period.pk],
                )
                draft_cnt = int(cursor.fetchone()[0] or 0)
                if draft_cnt > 0:
                    notifications.append(
                        {
                            "id": "draft-entries",
                            "level": "info",
                            "title": f"{draft_cnt} partida(s) en borrador",
                            "detail": f"Partidas pendientes de mayorizar en {active_period.label}.",
                            "to": "/libro-diario",
                        }
                    )

        return Response({"count": len(notifications), "items": notifications})
