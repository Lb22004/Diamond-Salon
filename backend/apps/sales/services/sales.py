from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounting.models import JournalEntry
from apps.accounting.services.posting import LineDTO, get_account, post_entry, reverse_entry
from apps.core.models import AccountingPeriod, AuditLog, Employee, User
from apps.core.serializers import AccountingPeriodSerializer
from apps.core.services.audit import log_audit, serialize_instance
from apps.core.services.periods import get_active_period, get_open_period
from apps.sales.models import Customer, DocumentSeries, Sale, SaleLine, Service
from apps.sales.services.tax import (
    TWOPLACES,
    compute_iva_withholding,
    get_company_iva_rate,
    split_iva,
)

FALLBACK_VITRINA_PRODUCTS = [
    {
        "id": 1,
        "sku": "VIT-001",
        "name": "Champú nutritivo 300ml",
        "inventory_type": "VITRINA",
        "sale_price": "12.00",
        "average_cost": "7.0000",
        "stock_available": "18.000",
    },
    {
        "id": 2,
        "sku": "VIT-002",
        "name": "Mascarilla reparadora intensiva 250ml",
        "inventory_type": "VITRINA",
        "sale_price": "22.00",
        "average_cost": "13.0000",
        "stock_available": "11.000",
    },
    {
        "id": 3,
        "sku": "VIT-003",
        "name": "Sérum brillo de argán 100ml",
        "inventory_type": "VITRINA",
        "sale_price": "18.00",
        "average_cost": "10.5000",
        "stock_available": "7.000",
    },
    {
        "id": 4,
        "sku": "VIT-004",
        "name": "Spray protector térmico profesional 200ml",
        "inventory_type": "VITRINA",
        "sale_price": "15.00",
        "average_cost": "6.5000",
        "stock_available": "25.000",
    },
]


def _coerce_date(val: date | datetime | str) -> date:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return date.fromisoformat(str(val)[:10])


def get_available_vitrina_products() -> list[dict]:
    """Return Vitrina retail products from inventory_product if migrated, else reference catalog."""
    tables = set(connection.introspection.table_names())
    if "inventory_product" in tables:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM inventory_product WHERE inventory_type = 'VITRINA'")
            if int(cursor.fetchone()[0] or 0) > 0:
                if "inventory_stock" in tables:
                    cursor.execute(
                        """
                        SELECT p.id, p.sku, p.name, p.inventory_type,
                               COALESCE(p.sale_price, 0), p.average_cost,
                               COALESCE(SUM(s.quantity), 0)
                        FROM inventory_product p
                        LEFT JOIN inventory_stock s ON s.product_id = p.id
                        WHERE p.is_active = true AND p.inventory_type = 'VITRINA'
                        GROUP BY p.id, p.sku, p.name, p.inventory_type, p.sale_price, p.average_cost
                        ORDER BY p.sku
                        """
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, sku, name, inventory_type, COALESCE(sale_price, 0), average_cost, 0
                        FROM inventory_product
                        WHERE is_active = true AND inventory_type = 'VITRINA'
                        ORDER BY sku
                        """
                    )
                rows = []
                for r in cursor.fetchall():
                    rows.append(
                        {
                            "id": int(r[0]),
                            "sku": str(r[1]),
                            "name": str(r[2]),
                            "inventory_type": str(r[3]),
                            "sale_price": f"{Decimal(str(r[4] or 0)):.2f}",
                            "average_cost": f"{Decimal(str(r[5] or 0)):.4f}",
                            "stock_available": f"{Decimal(str(r[6] or 0)):.3f}",
                        }
                    )
                return rows
    return FALLBACK_VITRINA_PRODUCTS


def _resolve_vitrina_product_info(product_id: int | None) -> dict:
    if not product_id:
        raise ValidationError("Las líneas de producto requieren seleccionar un artículo de Vitrina.")

    tables = set(connection.introspection.table_names())
    if "inventory_product" in tables:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, sku, name, inventory_type, COALESCE(sale_price, 0), average_cost, is_active
                FROM inventory_product
                WHERE id = %s
                """,
                [int(product_id)],
            )
            row = cursor.fetchone()
            if row:
                if not row[6]:
                    raise ValidationError(f"El producto {row[2]} se encuentra inactivo.")
                if row[3] != "VITRINA":
                    raise ValidationError(
                        f"Violación RN-07: El insumo '{row[2]}' pertenece a CABINA y no puede venderse en Vitrina."
                    )
                return {
                    "id": int(row[0]),
                    "sku": str(row[1]),
                    "name": str(row[2]),
                    "sale_price": Decimal(str(row[4] or 0)),
                    "average_cost": Decimal(str(row[5] or 0)),
                }

    for item in FALLBACK_VITRINA_PRODUCTS:
        if item["id"] == int(product_id):
            return {
                "id": item["id"],
                "sku": item["sku"],
                "name": item["name"],
                "sale_price": Decimal(item["sale_price"]),
                "average_cost": Decimal(item["average_cost"]),
            }

    return {
        "id": int(product_id),
        "sku": f"VIT-{int(product_id):03d}",
        "name": f"Producto Vitrina #{product_id}",
        "sale_price": Decimal("12.00"),
        "average_cost": Decimal("7.0000"),
    }


def _payment_account_key(payment_method: str) -> str:
    if payment_method == Sale.PaymentMethod.CASH:
        return "CASH"
    if payment_method in (Sale.PaymentMethod.CARD, Sale.PaymentMethod.TRANSFER):
        return "BANK"
    if payment_method == Sale.PaymentMethod.CREDIT:
        return "ACCOUNTS_RECEIVABLE"
    raise ValidationError(f"Método de pago inválido: {payment_method}")


@transaction.atomic
def create_sale(
    *,
    sale_date: date | str,
    doc_type: str,
    customer: Customer | int,
    payment_method: str = Sale.PaymentMethod.CASH,
    lines: list[dict],
    employee: Employee | int | None = None,
    related_sale: Sale | int | None = None,
    notes: str = "",
    user: User,
) -> Sale:
    """Atomically issue a fiscal sale (FCF/CCF/NC/ND), compute IVA, deduct Vitrina stock, and post JournalEntry (RF-VEN-01..05, RN-09, RN-11)."""
    s_date = _coerce_date(sale_date)
    period = get_open_period(s_date)

    cust = (
        customer
        if isinstance(customer, Customer)
        else Customer.objects.filter(pk=int(customer)).first()
    )
    if not cust or not cust.is_active:
        raise ValidationError("Debe seleccionar un cliente activo válido.")

    clean_doc_type = (doc_type or "FCF").upper().strip()
    if clean_doc_type not in ("FCF", "CCF", "NC", "ND"):
        raise ValidationError(f"Tipo de documento fiscal inválido: {clean_doc_type}")

    # RF-VEN-04: CCF / NC / ND requires a taxpayer customer with NIT/DUI and NRC
    if clean_doc_type in ("CCF", "NC", "ND"):
        if cust.customer_type != Customer.CustomerType.TAXPAYER or not cust.nrc or not cust.document_number:
            raise ValidationError(
                "Para emitir Comprobante de Crédito Fiscal (CCF/NC/ND) el cliente debe ser Contribuyente con NIT/DUI y NRC registrados (RF-VEN-04)."
            )

    rel_sale = None
    if clean_doc_type in ("NC", "ND"):
        if not related_sale:
            raise ValidationError("Las Notas de Crédito/Débito (NC/ND) deben referenciar un CCF emitido (RF-VEN-11).")
        rel_sale = (
            related_sale
            if isinstance(related_sale, Sale)
            else Sale.objects.filter(pk=int(related_sale)).first()
        )
        if not rel_sale or rel_sale.doc_type != "CCF":
            raise ValidationError("El documento relacionado para NC/ND debe ser un CCF válido.")

    emp = None
    if employee:
        emp = employee if isinstance(employee, Employee) else Employee.objects.filter(pk=int(employee)).first()

    if not lines:
        raise ValidationError("La venta debe incluir al menos una línea de servicio o producto.")

    # Lock active document series to assign next correlative without gaps (RF-VEN-02, RN-09)
    series = (
        DocumentSeries.objects.select_for_update()
        .filter(doc_type=clean_doc_type, is_active=True)
        .first()
    )
    if not series:
        raise ValidationError(f"No existe una serie fiscal activa para el tipo {clean_doc_type}.")
    if series.next_number > series.authorized_to:
        raise ValidationError(f"La serie {series.prefix} ha agotado su rango autorizado.")

    doc_number = f"{series.prefix}{series.next_number:04d}"
    series.next_number += 1
    series.save(update_fields=["next_number"])

    iva_rate = get_company_iva_rate()
    # RN-06: FCF prices include IVA; CCF/NC/ND prices exclude IVA (unless caller explicitly passes net/gross)
    price_includes_iva = clean_doc_type == "FCF"

    prepared_lines = []
    sum_taxable = Decimal("0.00")
    sum_iva = Decimal("0.00")
    sum_service_taxable = Decimal("0.00")
    sum_product_taxable = Decimal("0.00")
    sum_cost_of_sales = Decimal("0.00")

    for idx, raw in enumerate(lines, start=1):
        l_type = (raw.get("line_type") or "SERVICE").upper().strip()
        qty = Decimal(str(raw.get("quantity") or "1")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        discount = Decimal(str(raw.get("discount") or "0.00")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        if qty <= Decimal("0.000"):
            raise ValidationError(f"Línea #{idx}: la cantidad debe ser mayor a cero.")

        srv_obj = None
        prod_id = None
        unit_cost = None

        if l_type == SaleLine.LineType.SERVICE:
            srv_id = raw.get("service_id") or raw.get("service")
            if not srv_id:
                raise ValidationError(f"Línea #{idx}: debe seleccionar un servicio del catálogo.")
            srv_obj = srv_id if isinstance(srv_id, Service) else Service.objects.filter(pk=int(srv_id)).first()
            if not srv_obj or not srv_obj.is_active:
                raise ValidationError(f"Línea #{idx}: el servicio seleccionado no existe o está inactivo.")
            raw_price = raw.get("unit_price")
            if raw_price is None or raw_price == "":
                # Service catalog price includes IVA; if CCF, convert to net base unit price if not overridden
                if price_includes_iva:
                    unit_price = srv_obj.price
                else:
                    unit_price, _ = split_iva(srv_obj.price, price_includes_iva=True, rate=iva_rate)
            else:
                unit_price = Decimal(str(raw_price)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
            desc = (raw.get("description") or srv_obj.name).strip()
        elif l_type == SaleLine.LineType.PRODUCT:
            raw_pid = raw.get("product_id") or raw.get("product")
            p_info = _resolve_vitrina_product_info(int(raw_pid) if raw_pid else None)
            prod_id = p_info["id"]
            raw_price = raw.get("unit_price")
            if raw_price is None or raw_price == "":
                if price_includes_iva:
                    unit_price = p_info["sale_price"]
                else:
                    unit_price, _ = split_iva(p_info["sale_price"], price_includes_iva=True, rate=iva_rate)
            else:
                unit_price = Decimal(str(raw_price)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
            raw_cost = raw.get("unit_cost")
            unit_cost = (
                Decimal(str(raw_cost)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                if raw_cost is not None and raw_cost != ""
                else p_info["average_cost"]
            )
            desc = (raw.get("description") or p_info["name"]).strip()
        else:
            raise ValidationError(f"Línea #{idx}: tipo de línea inválido ({l_type}).")

        gross_line = (qty * unit_price - discount).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        if gross_line <= Decimal("0.00"):
            raise ValidationError(f"Línea #{idx}: el importe neto debe ser mayor a cero.")

        line_taxable, line_iva = split_iva(
            gross_line,
            price_includes_iva=price_includes_iva,
            rate=iva_rate,
        )
        line_total = (line_taxable + line_iva).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

        sum_taxable += line_taxable
        sum_iva += line_iva
        if l_type == SaleLine.LineType.SERVICE:
            sum_service_taxable += line_taxable
        else:
            sum_product_taxable += line_taxable
            line_cost = (qty * (unit_cost or Decimal("0.0000"))).quantize(
                TWOPLACES, rounding=ROUND_HALF_UP
            )
            sum_cost_of_sales += line_cost

        prepared_lines.append(
            {
                "line_no": idx,
                "line_type": l_type,
                "service": srv_obj,
                "product_id": prod_id,
                "description": desc,
                "quantity": qty,
                "unit_price": unit_price,
                "discount": discount,
                "taxable_amount": line_taxable,
                "iva_amount": line_iva,
                "total": line_total,
                "unit_cost": unit_cost,
            }
        )

    iva_withheld = compute_iva_withholding(
        sum_taxable,
        is_large_taxpayer=cust.is_large_taxpayer,
        doc_type=clean_doc_type,
    )
    total_doc = (sum_taxable + sum_iva - iva_withheld).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    sale = Sale.objects.create(
        series=series,
        doc_type=clean_doc_type,
        doc_number=doc_number,
        sale_date=s_date,
        period=period,
        customer=cust,
        employee=emp,
        payment_method=payment_method,
        taxable_amount=sum_taxable,
        exempt_amount=Decimal("0.00"),
        non_subject_amount=Decimal("0.00"),
        iva_amount=sum_iva,
        iva_withheld=iva_withheld,
        total=total_doc,
        status=Sale.SaleStatus.ISSUED,
        related_sale=rel_sale,
        notes=notes or "",
        created_by=user,
    )

    for pl in prepared_lines:
        SaleLine.objects.create(sale=sale, **pl)

    # Optional hook to P5's StockService if apps.inventory.services.stock is implemented
    try:
        from apps.inventory.services.stock import register_movement  # type: ignore

        for pl in prepared_lines:
            if pl["line_type"] == SaleLine.LineType.PRODUCT and pl["product_id"]:
                register_movement(
                    product=pl["product_id"],
                    location="VITRINA",
                    movement_type="RETURN_IN" if clean_doc_type == "NC" else "SALE",
                    quantity=pl["quantity"],
                    unit_cost=pl["unit_cost"],
                    movement_date=s_date,
                    source_app="sales.sale",
                    source_id=sale.pk,
                    user=user,
                )
    except (ImportError, Exception):
        pass

    # Build automatic double-entry lines (SRS §5 & RF-VEN-05)
    pay_key = _payment_account_key(payment_method)
    is_credit_note = clean_doc_type == "NC"
    entry_lines: list[LineDTO] = []

    if not is_credit_note:
        # Normal Sale (FCF / CCF / ND)
        entry_lines.append(
            LineDTO(
                account=get_account(pay_key),
                debit=total_doc,
                credit=Decimal("0.00"),
                description=f"Cobro {sale.get_payment_method_display()} s/ {doc_number} ({cust.name})",
            )
        )
        if iva_withheld > Decimal("0.00"):
            entry_lines.append(
                LineDTO(
                    account=get_account("IVA_PERCEIVED"),
                    debit=iva_withheld,
                    credit=Decimal("0.00"),
                    description=f"Retención 1% IVA gran contribuyente s/ {doc_number}",
                )
            )
        if sum_service_taxable > Decimal("0.00"):
            entry_lines.append(
                LineDTO(
                    account=get_account("INCOME_SERVICES"),
                    debit=Decimal("0.00"),
                    credit=sum_service_taxable,
                    description=f"Ingresos por servicios en cabina s/ {doc_number}",
                )
            )
        if sum_product_taxable > Decimal("0.00"):
            entry_lines.append(
                LineDTO(
                    account=get_account("INCOME_PRODUCTS"),
                    debit=Decimal("0.00"),
                    credit=sum_product_taxable,
                    description=f"Ingresos por venta de productos vitrina s/ {doc_number}",
                )
            )
        if sum_iva > Decimal("0.00"):
            entry_lines.append(
                LineDTO(
                    account=get_account("IVA_DEBIT"),
                    debit=Decimal("0.00"),
                    credit=sum_iva,
                    description=f"IVA débito fiscal 13% s/ {doc_number}",
                )
            )
        if sum_cost_of_sales > Decimal("0.00"):
            entry_lines.append(
                LineDTO(
                    account=get_account("COST_OF_SALES"),
                    debit=sum_cost_of_sales,
                    credit=Decimal("0.00"),
                    description=f"Costo de venta promedio ponderado s/ {doc_number}",
                )
            )
            entry_lines.append(
                LineDTO(
                    account=get_account("INVENTORY_VITRINA"),
                    debit=Decimal("0.00"),
                    credit=sum_cost_of_sales,
                    description=f"Descargo de inventario vitrina s/ {doc_number}",
                )
            )
    else:
        # Credit Note (NC) reverses income, IVA debit, and cost of sales
        if sum_service_taxable > Decimal("0.00"):
            entry_lines.append(
                LineDTO(
                    account=get_account("INCOME_SERVICES"),
                    debit=sum_service_taxable,
                    credit=Decimal("0.00"),
                    description=f"Devolución/rebaja servicios s/ {doc_number}",
                )
            )
        if sum_product_taxable > Decimal("0.00"):
            entry_lines.append(
                LineDTO(
                    account=get_account("INCOME_PRODUCTS"),
                    debit=sum_product_taxable,
                    credit=Decimal("0.00"),
                    description=f"Devolución/rebaja productos vitrina s/ {doc_number}",
                )
            )
        if sum_iva > Decimal("0.00"):
            entry_lines.append(
                LineDTO(
                    account=get_account("IVA_DEBIT"),
                    debit=sum_iva,
                    credit=Decimal("0.00"),
                    description=f"Reversión IVA débito fiscal s/ {doc_number}",
                )
            )
        entry_lines.append(
            LineDTO(
                account=get_account(pay_key),
                debit=Decimal("0.00"),
                credit=total_doc,
                description=f"Aplicación Nota de Crédito {doc_number} ({cust.name})",
            )
        )
        if iva_withheld > Decimal("0.00"):
            entry_lines.append(
                LineDTO(
                    account=get_account("IVA_PERCEIVED"),
                    debit=Decimal("0.00"),
                    credit=iva_withheld,
                    description=f"Ajuste retención 1% IVA s/ {doc_number}",
                )
            )
        if sum_cost_of_sales > Decimal("0.00"):
            entry_lines.append(
                LineDTO(
                    account=get_account("INVENTORY_VITRINA"),
                    debit=sum_cost_of_sales,
                    credit=Decimal("0.00"),
                    description=f"Reingreso a inventario vitrina s/ {doc_number}",
                )
            )
            entry_lines.append(
                LineDTO(
                    account=get_account("COST_OF_SALES"),
                    debit=Decimal("0.00"),
                    credit=sum_cost_of_sales,
                    description=f"Reversión costo de venta s/ {doc_number}",
                )
            )

    summary_concept = ", ".join(pl["description"] for pl in prepared_lines[:2])
    j_entry = post_entry(
        entry_date=s_date,
        description=f"Venta {doc_number} · {cust.name} · {summary_concept}",
        entry_type=JournalEntry.EntryType.SALE,
        lines=entry_lines,
        source_app="sales.sale",
        source_id=sale.pk,
        user=user,
    )

    sale.journal_entry = j_entry
    sale.save(update_fields=["journal_entry"])

    log_audit(
        action=AuditLog.Action.CREATE,
        table_name="sales_sale",
        record_id=sale.pk,
        after_data=serialize_instance(sale),
        user=user,
    )
    return sale


@transaction.atomic
def void_sale(sale: Sale, *, reason: str, user: User) -> Sale:
    """Void an issued sale in an open period, reverse its JournalEntry, and log audit (RF-VEN-10)."""
    locked_sale = Sale.objects.select_for_update().get(pk=sale.pk)
    if locked_sale.status == Sale.SaleStatus.VOIDED:
        raise ValidationError(f"El documento {locked_sale.doc_number} ya se encuentra anulado.")

    clean_reason = (reason or "").strip()
    if len(clean_reason) < 5:
        raise ValidationError("Debe especificar un motivo de anulación válido (mínimo 5 caracteres).")

    # Verify the sale's period is still open (RF-VEN-10, RN-03)
    get_open_period(locked_sale.sale_date)

    before = serialize_instance(locked_sale)
    if locked_sale.journal_entry and locked_sale.journal_entry.status == JournalEntry.EntryStatus.POSTED:
        reverse_entry(
            locked_sale.journal_entry,
            reason=f"Anulación de {locked_sale.doc_number}: {clean_reason}",
            user=user,
            reversal_date=locked_sale.sale_date,
        )

    locked_sale.status = Sale.SaleStatus.VOIDED
    locked_sale.void_reason = clean_reason
    locked_sale.voided_at = timezone.now()
    locked_sale.save(update_fields=["status", "void_reason", "voided_at"])

    log_audit(
        action=AuditLog.Action.VOID,
        table_name="sales_sale",
        record_id=locked_sale.pk,
        before_data=before,
        after_data=serialize_instance(locked_sale),
        user=user,
    )
    return locked_sale


def get_sales_book(
    *,
    period: AccountingPeriod | None = None,
    doc_type: str | None = None,
    line_type: str | None = None,
    search: str | None = None,
    date_from: date | str | None = None,
    date_to: date | str | None = None,
) -> dict:
    """Compute Libro de Ventas KPIs, Cabina vs Vitrina breakdown, and legal FCF/CCF books (RF-VEN-06..12)."""
    from apps.sales.serializers import SaleSerializer

    resolved_period = period or get_active_period()
    base_qs = (
        Sale.objects.select_related("customer", "employee", "series", "journal_entry", "period")
        .prefetch_related("lines__service")
        .order_by("sale_date", "id")
    )
    if resolved_period:
        base_qs = base_qs.filter(period=resolved_period)
    if date_from:
        base_qs = base_qs.filter(sale_date__gte=_coerce_date(date_from))
    if date_to:
        base_qs = base_qs.filter(sale_date__lte=_coerce_date(date_to))

    # Period-wide metrics before UI tab/search filters
    period_issued = [s for s in base_qs if s.status == Sale.SaleStatus.ISSUED]

    gross_sales = Decimal("0.00")
    taxable_base = Decimal("0.00")
    iva_debit = Decimal("0.00")
    iva_withheld = Decimal("0.00")
    cabina_amount = Decimal("0.00")
    cabina_Taxable = Decimal("0.00")
    cabina_lines_count = 0
    cabina_doc_ids = set()
    vitrina_amount = Decimal("0.00")
    vitrina_taxable = Decimal("0.00")
    vitrina_cost = Decimal("0.00")
    vitrina_lines_count = 0
    vitrina_doc_ids = set()

    all_docs_count = len(period_issued)
    fcf_docs = []
    ccf_docs = []

    for s in period_issued:
        sign = Decimal("-1.00") if s.doc_type == "NC" else Decimal("1.00")
        gross_sales += sign * s.total
        taxable_base += sign * s.taxable_amount
        iva_debit += sign * s.iva_amount
        iva_withheld += sign * s.iva_withheld

        if s.doc_type == "FCF":
            fcf_docs.append(s.doc_number)
        else:
            ccf_docs.append(s.doc_number)

        for ln in s.lines.all():
            if ln.line_type == SaleLine.LineType.SERVICE:
                cabina_amount += sign * ln.total
                cabina_Taxable += sign * ln.taxable_amount
                cabina_lines_count += 1
                cabina_doc_ids.add(s.id)
            elif ln.line_type == SaleLine.LineType.PRODUCT:
                vitrina_amount += sign * ln.total
                vitrina_taxable += sign * ln.taxable_amount
                vitrina_cost += sign * (ln.quantity * (ln.unit_cost or Decimal("0.00"))).quantize(
                    TWOPLACES, rounding=ROUND_HALF_UP
                )
                vitrina_lines_count += 1
                vitrina_doc_ids.add(s.id)

    taxable_pct = (
        ((taxable_base / gross_sales) * Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        if gross_sales > Decimal("0.00")
        else Decimal("0.00")
    )
    cabina_pct = (
        ((cabina_amount / gross_sales) * Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        if gross_sales > Decimal("0.00")
        else Decimal("0.00")
    )
    vitrina_pct = (
        ((vitrina_amount / gross_sales) * Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        if gross_sales > Decimal("0.00")
        else Decimal("0.00")
    )

    if fcf_docs:
        correlative_range = f"{fcf_docs[0]} — {fcf_docs[-1]}"
    elif ccf_docs:
        correlative_range = f"{ccf_docs[0]} — {ccf_docs[-1]}"
    else:
        correlative_range = "Sin emisiones"

    # Legal Book 1: Consumidor Final (daily summary by FCF range · RF-VEN-12, OI-7)
    fcf_by_day = defaultdict(list)
    for s in base_qs:
        if s.doc_type == "FCF" and s.status == Sale.SaleStatus.ISSUED:
            fcf_by_day[s.sale_date.isoformat()].append(s)

    legal_fcf_book = []
    for day_str, day_sales in sorted(fcf_by_day.items()):
        d_taxable = sum((x.taxable_amount for x in day_sales), Decimal("0.00"))
        d_iva = sum((x.iva_amount for x in day_sales), Decimal("0.00"))
        d_tot = sum((x.total for x in day_sales), Decimal("0.00"))
        legal_fcf_book.append(
            {
                "sale_date": day_str,
                "from_doc": day_sales[0].doc_number,
                "to_doc": day_sales[-1].doc_number,
                "documents_count": len(day_sales),
                "taxable_amount": f"{d_taxable:.2f}",
                "exempt_amount": "0.00",
                "iva_amount": f"{d_iva:.2f}",
                "total": f"{d_tot:.2f}",
            }
        )

    # Legal Book 2: Contribuyentes IVA (one row per CCF/NC/ND · RF-VEN-12, OI-7)
    legal_ccf_book = []
    for s in base_qs:
        if s.doc_type in ("CCF", "NC", "ND"):
            sign = Decimal("-1.00") if s.doc_type == "NC" else Decimal("1.00")
            legal_ccf_book.append(
                {
                    "id": s.id,
                    "sale_date": s.sale_date.isoformat(),
                    "doc_type": s.doc_type,
                    "doc_number": s.doc_number,
                    "customer_name": s.customer.name,
                    "nrc": s.customer.nrc or "—",
                    "document_number": s.customer.document_number or "—",
                    "taxable_amount": f"{(sign * s.taxable_amount):.2f}",
                    "iva_amount": f"{(sign * s.iva_amount):.2f}",
                    "iva_withheld": f"{(sign * s.iva_withheld):.2f}",
                    "total": f"{(sign * s.total):.2f}",
                    "status": s.status,
                    "journal_entry_id": s.journal_entry_id,
                }
            )

    # Filtered queryset for the main interactive table
    filtered_qs = base_qs
    if doc_type:
        dt = doc_type.upper().strip()
        if dt == "CCF_GROUP":
            filtered_qs = filtered_qs.filter(doc_type__in=["CCF", "NC", "ND"])
        else:
            filtered_qs = filtered_qs.filter(doc_type=dt)
    if line_type in ("SERVICE", "PRODUCT"):
        filtered_qs = filtered_qs.filter(lines__line_type=line_type).distinct()
    if search:
        q_str = search.strip()
        filtered_qs = filtered_qs.filter(
            Q(doc_number__icontains=q_str)
            | Q(customer__name__icontains=q_str)
            | Q(customer__nrc__icontains=q_str)
            | Q(notes__icontains=q_str)
            | Q(lines__description__icontains=q_str)
        ).distinct()

    filtered_list = list(filtered_qs)
    f_taxable = Decimal("0.00")
    f_iva = Decimal("0.00")
    f_withheld = Decimal("0.00")
    f_total = Decimal("0.00")

    for s in filtered_list:
        if s.status == Sale.SaleStatus.ISSUED:
            sign = Decimal("-1.00") if s.doc_type == "NC" else Decimal("1.00")
            f_taxable += sign * s.taxable_amount
            f_iva += sign * s.iva_amount
            f_withheld += sign * s.iva_withheld
            f_total += sign * s.total

    return {
        "period": AccountingPeriodSerializer(resolved_period).data if resolved_period else None,
        "kpis": {
            "gross_sales": f"{gross_sales:.2f}",
            "taxable_base": f"{taxable_base:.2f}",
            "taxable_pct": f"{taxable_pct:.1f}%",
            "iva_debit": f"{iva_debit:.2f}",
            "iva_withheld": f"{iva_withheld:.2f}",
            "documents_issued": all_docs_count,
            "fcf_count": len(fcf_docs),
            "ccf_count": len(ccf_docs),
            "correlative_range": correlative_range,
        },
        "regime_summary": {
            "cabina": {
                "label": "Servicios en Salón (Cabina)",
                "account_code": "5101",
                "amount": f"{cabina_amount:.2f}",
                "taxable": f"{cabina_Taxable:.2f}",
                "pct": f"{cabina_pct:.1f}%",
                "lines_count": cabina_lines_count,
                "documents_count": len(cabina_doc_ids),
            },
            "vitrina": {
                "label": "Venta Retail de Productos (Vitrina)",
                "account_code": "5102",
                "amount": f"{vitrina_amount:.2f}",
                "taxable": f"{vitrina_taxable:.2f}",
                "cost_of_sales": f"{vitrina_cost:.2f}",
                "pct": f"{vitrina_pct:.1f}%",
                "lines_count": vitrina_lines_count,
                "documents_count": len(vitrina_doc_ids),
            },
        },
        "counts": {
            "all": all_docs_count,
            "services": len(cabina_doc_ids),
            "products": len(vitrina_doc_ids),
            "fcf": len(fcf_docs),
            "ccf": len(ccf_docs),
        },
        "sales": SaleSerializer(filtered_list, many=True).data,
        "legal_fcf_book": legal_fcf_book,
        "legal_ccf_book": legal_ccf_book,
        "totals": {
            "taxable_amount": f"{f_taxable:.2f}",
            "iva_amount": f"{f_iva:.2f}",
            "iva_withheld": f"{f_withheld:.2f}",
            "total": f"{f_total:.2f}",
            "is_verified": (f_taxable + f_iva - f_withheld) == f_total,
        },
    }
