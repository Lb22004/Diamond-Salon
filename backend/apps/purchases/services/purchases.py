from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.accounting.models import Account, JournalEntry
from apps.accounting.services.posting import LineDTO, get_account, post_entry, reverse_entry
from apps.core.models import AccountingPeriod, AuditLog
from apps.core.services.audit import log_audit, serialize_instance
from apps.core.services.periods import get_open_period
from apps.inventory.models import InventoryMovement, Location, Product
from apps.inventory.services.stock import RegimeMismatchError, register_movement
from apps.purchases.models import Purchase, PurchaseLine, Supplier, SupplierPayment

Q2 = Decimal("0.01")
Q3 = Decimal("0.001")
Q4 = Decimal("0.0001")
IVA_RATE = Decimal("0.13")
PERCEPTION_RATE = Decimal("0.01")


def _coerce_date(val: date | datetime | str) -> date:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return date.fromisoformat(str(val)[:10])


@transaction.atomic
def create_purchase(
    *,
    supplier_id: int,
    doc_type: str = "CCF",
    doc_number: str,
    doc_date: date | str,
    destination: str = "VITRINA",
    payment_condition: str = "CREDIT",
    due_date: date | str | None = None,
    lines: list[dict],
    apply_perception: bool = False,
    notes: str = "",
    user,
) -> Purchase:
    """
    Register a purchase document, atomically updating Kárdex stock & weighted-average cost
    and posting the double-entry journal entry (RF-COM-02..04, RN-07).
    """
    p_date = _coerce_date(doc_date)
    period = get_open_period(p_date)

    supplier = Supplier.objects.filter(pk=int(supplier_id), is_active=True).first()
    if not supplier:
        raise ValidationError("El proveedor seleccionado no existe o está inactivo.")

    clean_doc_type = str(doc_type or "CCF").upper()
    clean_doc_num = str(doc_number or "").strip().upper()
    if not clean_doc_num:
        raise ValidationError("El número de comprobante de compra es obligatorio.")

    if Purchase.objects.filter(supplier=supplier, doc_type=clean_doc_type, doc_number=clean_doc_num).exists():
        raise ValidationError(
            f"Ya existe el documento {clean_doc_type} {clean_doc_num} registrado para el proveedor {supplier.name} (RF-COM-03)."
        )

    clean_dest = str(destination or "VITRINA").upper()
    clean_cond = str(payment_condition or "CREDIT").upper()
    parsed_due = _coerce_date(due_date) if due_date else None
    if clean_cond == Purchase.PaymentCondition.CREDIT and not parsed_due:
        parsed_due = period.end_date

    if not lines:
        raise ValidationError("La compra debe incluir al menos una línea de detalle.")

    has_iva_credit = clean_doc_type in (
        Purchase.DocType.CCF,
        Purchase.DocType.ND,
        Purchase.DocType.IMPORT,
    )

    prepared_lines = []
    sum_taxable = Decimal("0.00")
    sum_iva = Decimal("0.00")
    vitrina_debit = Decimal("0.00")
    cabina_debit = Decimal("0.00")
    expense_debits: list[tuple[Account, Decimal, str]] = []

    for idx, raw in enumerate(lines, start=1):
        qty = Decimal(str(raw.get("quantity", 1))).quantize(Q3, rounding=ROUND_HALF_UP)
        unit_cost = Decimal(str(raw.get("unit_cost", 0))).quantize(Q4, rounding=ROUND_HALF_UP)
        if qty <= Decimal("0.000") or unit_cost <= Decimal("0.0000"):
            raise ValidationError(f"Línea #{idx}: cantidad y costo unitario deben ser mayores a cero.")

        line_taxable = (qty * unit_cost).quantize(Q2, rounding=ROUND_HALF_UP)
        line_iva = (
            (line_taxable * IVA_RATE).quantize(Q2, rounding=ROUND_HALF_UP)
            if has_iva_credit
            else Decimal("0.00")
        )

        prod_id = raw.get("product_id") or raw.get("product")
        exp_acc_id = raw.get("expense_account_id") or raw.get("expense_account")

        if prod_id:
            prod = Product.objects.select_for_update().filter(pk=int(prod_id), is_active=True).first()
            if not prod:
                raise ValidationError(f"Línea #{idx}: el producto seleccionado no existe.")

            # Enforce RN-07 destination consistency
            if clean_dest == Purchase.Destination.VITRINA and prod.inventory_type != Product.InventoryType.VITRINA:
                raise RegimeMismatchError(
                    f"RN-07: La compra tiene destino VITRINA pero el artículo «{prod.name}» es de CABINA."
                )
            if clean_dest == Purchase.Destination.CABINA and prod.inventory_type != Product.InventoryType.CABINA:
                raise RegimeMismatchError(
                    f"RN-07: La compra tiene destino CABINA pero el artículo «{prod.name}» es de VITRINA."
                )

            loc_raw = raw.get("location_id") or raw.get("location")
            if loc_raw:
                loc = (
                    Location.objects.filter(pk=int(loc_raw)).first()
                    if str(loc_raw).isdigit()
                    else Location.objects.filter(code__iexact=str(loc_raw)).first()
                )
            else:
                loc = (
                    Location.objects.filter(location_type=prod.inventory_type, is_active=True).first()
                    or Location.objects.filter(is_active=True).first()
                )
            if not loc:
                raise ValidationError(f"Línea #{idx}: ubicación de inventario inválida.")

            if prod.inventory_type == Product.InventoryType.VITRINA:
                vitrina_debit += line_taxable
            else:
                cabina_debit += line_taxable

            prepared_lines.append(
                {
                    "line_no": idx,
                    "product": prod,
                    "expense_account": None,
                    "location": loc,
                    "description": raw.get("description") or prod.name,
                    "quantity": qty,
                    "unit_cost": unit_cost,
                    "taxable_amount": line_taxable,
                    "iva_amount": line_iva,
                }
            )
        elif exp_acc_id:
            exp_acc = (
                Account.objects.filter(pk=int(exp_acc_id)).first()
                if str(exp_acc_id).isdigit()
                else Account.objects.filter(code=str(exp_acc_id)).first()
            )
            if not exp_acc:
                raise ValidationError(f"Línea #{idx}: cuenta de gasto inválida.")
            desc = raw.get("description") or f"Gasto s/ {clean_doc_num}"
            expense_debits.append((exp_acc, line_taxable, desc))
            prepared_lines.append(
                {
                    "line_no": idx,
                    "product": None,
                    "expense_account": exp_acc,
                    "location": None,
                    "description": desc,
                    "quantity": qty,
                    "unit_cost": unit_cost,
                    "taxable_amount": line_taxable,
                    "iva_amount": line_iva,
                }
            )
        else:
            raise ValidationError(f"Línea #{idx}: debe seleccionar un producto de inventario o una cuenta de gasto.")

        sum_taxable += line_taxable
        sum_iva += line_iva

    # 1% IVA perception from LARGE suppliers when applicable (RF-COM-03)
    iva_perceived = Decimal("0.00")
    if (
        apply_perception
        and supplier.taxpayer_category == Supplier.TaxpayerCategory.LARGE
        and has_iva_credit
        and sum_taxable >= Decimal("100.00")
    ):
        iva_perceived = (sum_taxable * PERCEPTION_RATE).quantize(Q2, rounding=ROUND_HALF_UP)

    total_doc = (sum_taxable + sum_iva + iva_perceived).quantize(Q2, rounding=ROUND_HALF_UP)
    is_cash = clean_cond == Purchase.PaymentCondition.CASH

    purchase = Purchase.objects.create(
        supplier=supplier,
        doc_type=clean_doc_type,
        doc_number=clean_doc_num,
        doc_date=p_date,
        period=period,
        destination=clean_dest,
        taxable_amount=sum_taxable,
        exempt_amount=Decimal("0.00"),
        iva_credit=sum_iva,
        iva_perceived=iva_perceived,
        total=total_doc,
        payment_condition=clean_cond,
        due_date=parsed_due,
        amount_paid=total_doc if is_cash else Decimal("0.00"),
        payment_status=Purchase.PaymentStatus.PAID if is_cash else Purchase.PaymentStatus.PENDING,
        status=Purchase.Status.REGISTERED,
        notes=notes or "",
        created_by=user,
    )

    movements: list[InventoryMovement] = []
    for pl in prepared_lines:
        PurchaseLine.objects.create(purchase=purchase, **pl)
        if pl["product"] is not None:
            mov = register_movement(
                product=pl["product"],
                location=pl["location"],
                movement_type=InventoryMovement.MovementType.PURCHASE,
                quantity=pl["quantity"],
                unit_cost=pl["unit_cost"],
                movement_date=p_date,
                source_app="purchases.purchase",
                source_id=purchase.pk,
                notes=f"Compra {clean_doc_type} {clean_doc_num} — {supplier.name}",
                user=user,
            )
            movements.append(mov)

    # Build double-entry lines (RF-COM-04b)
    j_lines: list[LineDTO] = []
    if vitrina_debit > Decimal("0.00"):
        j_lines.append(
            LineDTO(
                account=get_account("INVENTORY_VITRINA"),
                debit=vitrina_debit,
                description=f"Ingreso mercadería Vitrina s/ {clean_doc_num} ({supplier.name})",
            )
        )
    if cabina_debit > Decimal("0.00"):
        j_lines.append(
            LineDTO(
                account=get_account("INVENTORY_CABINA"),
                debit=cabina_debit,
                description=f"Ingreso insumos Cabina s/ {clean_doc_num} ({supplier.name})",
            )
        )
    for exp_acc, exp_amt, exp_desc in expense_debits:
        j_lines.append(LineDTO(account=exp_acc, debit=exp_amt, description=exp_desc))

    if sum_iva > Decimal("0.00"):
        j_lines.append(
            LineDTO(
                account=get_account("IVA_CREDIT"),
                debit=sum_iva,
                description=f"IVA crédito fiscal 13% s/ {clean_doc_type} {clean_doc_num}",
            )
        )
    if iva_perceived > Decimal("0.00"):
        j_lines.append(
            LineDTO(
                account=get_account("IVA_PERCEIVED"),
                debit=iva_perceived,
                description=f"IVA percibido 1% s/ {clean_doc_type} {clean_doc_num}",
            )
        )

    credit_key = "CASH" if is_cash else "ACCOUNTS_PAYABLE"
    j_lines.append(
        LineDTO(
            account=get_account(credit_key),
            credit=total_doc,
            description=(
                f"Pago de contado {clean_doc_num} a {supplier.name}"
                if is_cash
                else f"Cuenta por pagar a {supplier.name} s/ {clean_doc_num}"
            ),
        )
    )

    j_entry = post_entry(
        entry_date=p_date,
        description=f"Compra {clean_doc_type} {clean_doc_num} {supplier.name} — Destino {purchase.get_destination_display()}",
        lines=j_lines,
        entry_type=JournalEntry.EntryType.PURCHASE,
        source_app="purchases.purchase",
        source_id=purchase.pk,
        user=user,
    )
    purchase.journal_entry = j_entry
    purchase.save(update_fields=["journal_entry"])

    if movements:
        InventoryMovement.objects.filter(pk__in=[m.pk for m in movements]).update(journal_entry=j_entry)

    if is_cash:
        SupplierPayment.objects.create(
            purchase=purchase,
            payment_date=p_date,
            amount=total_doc,
            payment_method=SupplierPayment.PaymentMethod.CASH,
            reference=f"Contado {clean_doc_num}",
            cash_account=get_account("CASH"),
            journal_entry=j_entry,
            created_by=user,
        )

    log_audit(
        user=user,
        action=AuditLog.Action.CREATE,
        table_name="purchases_purchase",
        record_id=purchase.pk,
        after_data=serialize_instance(purchase),
    )
    return purchase


@transaction.atomic
def register_supplier_payment(
    *,
    purchase: Purchase | int,
    payment_date: date | str,
    amount: Decimal | int | float | str,
    payment_method: str = "CASH",
    reference: str = "",
    cash_account_id: int | None = None,
    user,
) -> SupplierPayment:
    """
    Register a partial or full supplier payment against a purchase, updating
    payment_status and posting Dr 210101 Proveedores / Cr Caja or Bancos (RF-COM-09).
    """
    pay_date = _coerce_date(payment_date)
    get_open_period(pay_date)

    pur = (
        Purchase.objects.select_for_update().get(pk=purchase.pk)
        if isinstance(purchase, Purchase)
        else Purchase.objects.select_for_update().get(pk=int(purchase))
    )
    if pur.status == Purchase.Status.VOIDED:
        raise ValidationError("No se puede registrar pagos sobre una compra anulada.")

    amt = Decimal(str(amount)).quantize(Q2, rounding=ROUND_HALF_UP)
    balance_due = (pur.total - pur.amount_paid).quantize(Q2)
    if amt <= Decimal("0.00"):
        raise ValidationError("El monto del abono debe ser mayor a $0.00.")
    if amt > balance_due:
        raise ValidationError(
            f"El monto del pago (${amt:.2f}) excede el saldo pendiente de la compra (${balance_due:.2f})."
        )

    clean_method = str(payment_method or "CASH").upper()
    if cash_account_id:
        cash_acc = Account.objects.get(pk=int(cash_account_id))
    else:
        cash_acc = get_account("CASH" if clean_method == "CASH" else "BANK")

    j_entry = post_entry(
        entry_date=pay_date,
        description=f"Pago a proveedor {pur.supplier.name} — Abono a {pur.doc_type} {pur.doc_number}",
        lines=[
            LineDTO(
                account=get_account("ACCOUNTS_PAYABLE"),
                debit=amt,
                description=f"Abono/liquidación {pur.doc_number} {pur.supplier.name}",
            ),
            LineDTO(
                account=cash_acc,
                credit=amt,
                description=f"Egreso por pago a proveedor ({reference or clean_method})",
            ),
        ],
        entry_type=JournalEntry.EntryType.PAYMENT,
        source_app="purchases.supplierpayment",
        source_id=pur.pk,
        user=user,
    )

    payment = SupplierPayment.objects.create(
        purchase=pur,
        payment_date=pay_date,
        amount=amt,
        payment_method=clean_method,
        reference=reference or f"Abono {pur.doc_number}",
        cash_account=cash_acc,
        journal_entry=j_entry,
        created_by=user,
    )

    new_paid = (pur.amount_paid + amt).quantize(Q2)
    pur.amount_paid = new_paid
    pur.payment_status = (
        Purchase.PaymentStatus.PAID if new_paid >= pur.total else Purchase.PaymentStatus.PARTIAL
    )
    pur.save(update_fields=["amount_paid", "payment_status"])

    log_audit(
        user=user,
        action=AuditLog.Action.CREATE,
        table_name="purchases_supplier_payment",
        record_id=payment.pk,
        after_data=serialize_instance(payment),
    )
    return payment


@transaction.atomic
def void_purchase(purchase: Purchase | int, *, reason: str, user) -> Purchase:
    """
    Void a registered purchase, reversing its stock movements and journal entry.
    Blocked if the stock was already consumed or if payments exist (RF-COM-11).
    """
    if not reason or not reason.strip():
        raise ValidationError("Debe especificar un motivo de anulación para la compra.")

    pur = (
        Purchase.objects.select_for_update().get(pk=purchase.pk)
        if isinstance(purchase, Purchase)
        else Purchase.objects.select_for_update().get(pk=int(purchase))
    )
    if pur.status == Purchase.Status.VOIDED:
        raise ValidationError("Esta compra ya se encuentra anulada.")

    get_open_period(pur.doc_date)

    if pur.amount_paid > Decimal("0.00") and pur.payment_condition == Purchase.PaymentCondition.CREDIT:
        raise ValidationError(
            "No se puede anular una compra al crédito que ya tiene pagos aplicados. Revierta primero el pago."
        )

    # Reverse stock movements (raises InsufficientStockError if stock was already consumed)
    for line in pur.lines.select_related("product", "location").all():
        if line.product and line.location:
            register_movement(
                product=line.product,
                location=line.location,
                movement_type=InventoryMovement.MovementType.RETURN_OUT,
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                movement_date=pur.doc_date,
                source_app="purchases.purchase.void",
                source_id=pur.pk,
                notes=f"Anulación {pur.doc_number}: {reason.strip()}",
                user=user,
            )

    if pur.journal_entry and pur.journal_entry.status == JournalEntry.EntryStatus.POSTED:
        linked_count = Purchase.objects.filter(journal_entry=pur.journal_entry, status="REGISTERED").count()
        if linked_count <= 1:
            reverse_entry(
                pur.journal_entry,
                reason=reason.strip(),
                user=user,
                reversal_date=pur.doc_date,
            )

    before_snap = serialize_instance(pur)
    pur.status = Purchase.Status.VOIDED
    pur.void_reason = reason.strip()
    pur.save(update_fields=["status", "void_reason"])

    log_audit(
        user=user,
        action=AuditLog.Action.VOID,
        table_name="purchases_purchase",
        record_id=pur.pk,
        before_data=before_snap,
        after_data=serialize_instance(pur),
    )
    return pur


def get_purchase_book(
    *,
    period: AccountingPeriod | int | None = None,
    supplier_id: int | str | None = None,
    destination: str = "",
    search: str = "",
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """
    Build complete payload for Vista 4 · Libro de compras (RF-COM-05..10, RF-COM-12)
    matching the reference mock-up.
    """
    if isinstance(period, AccountingPeriod):
        period_obj = period
    elif period:
        period_obj = AccountingPeriod.objects.filter(pk=int(period)).first()
    else:
        period_obj = (
            AccountingPeriod.objects.filter(is_active=True).first()
            or AccountingPeriod.objects.filter(year=2026, month=11).first()
        )

    qs = (
        Purchase.objects.select_related("supplier", "period", "journal_entry")
        .prefetch_related("lines__product", "lines__location", "payments")
        .order_by("doc_date", "id")
    )
    if period_obj:
        qs = qs.filter(period=period_obj)
    if supplier_id:
        qs = qs.filter(supplier_id=int(supplier_id))
    if destination and destination.upper() in ("VITRINA", "CABINA", "MIXED", "EXPENSE"):
        qs = qs.filter(destination=destination.upper())
    if date_from:
        qs = qs.filter(doc_date__gte=_coerce_date(date_from))
    if date_to:
        qs = qs.filter(doc_date__lte=_coerce_date(date_to))
    if search:
        q = search.strip()
        qs = qs.filter(
            models.Q(doc_number__icontains=q)
            | models.Q(supplier__name__icontains=q)
            | models.Q(supplier__brands_description__icontains=q)
            | models.Q(supplier__nrc__icontains=q)
        )

    active_purchases = [p for p in qs if p.status == Purchase.Status.REGISTERED]
    total_taxable = sum((p.taxable_amount for p in active_purchases), Decimal("0.00"))
    total_exempt = sum((p.exempt_amount for p in active_purchases), Decimal("0.00"))
    total_iva = sum((p.iva_credit for p in active_purchases), Decimal("0.00"))
    total_perceived = sum((p.iva_perceived for p in active_purchases), Decimal("0.00"))
    total_amount = sum((p.total for p in active_purchases), Decimal("0.00"))

    # Distribution by destination (Vitrina vs Cabina) for all registered purchases in period
    period_all = (
        Purchase.objects.filter(period=period_obj, status=Purchase.Status.REGISTERED)
        if period_obj
        else Purchase.objects.filter(status=Purchase.Status.REGISTERED)
    )
    vit_total = sum(
        (p.total for p in period_all if p.destination == Purchase.Destination.VITRINA),
        Decimal("0.00"),
    )
    cab_total = sum(
        (p.total for p in period_all if p.destination == Purchase.Destination.CABINA),
        Decimal("0.00"),
    )
    exp_total = sum(
        (p.total for p in period_all if p.destination in (Purchase.Destination.EXPENSE, Purchase.Destination.MIXED)),
        Decimal("0.00"),
    )
    dist_base = vit_total + cab_total + exp_total
    vit_pct = int(round((vit_total / dist_base) * 100)) if dist_base > 0 else 50
    cab_pct = int(round((cab_total / dist_base) * 100)) if dist_base > 0 else 50

    active_suppliers = list(Supplier.objects.filter(is_active=True).order_by("id"))
    supplier_names_summary = ", ".join(s.name for s in active_suppliers[:3])

    rows = []
    for p in qs:
        balance_due = max(Decimal("0.00"), (p.total - p.amount_paid).quantize(Q2))
        rows.append(
            {
                "id": p.id,
                "doc_date": p.doc_date.isoformat(),
                "doc_type": p.doc_type,
                "doc_number": p.doc_number,
                "supplier_id": p.supplier_id,
                "supplier_name": p.supplier.name,
                "supplier_brands": p.supplier.brands_description or "",
                "supplier_nit": p.supplier.nit,
                "supplier_nrc": p.supplier.nrc or "",
                "destination": p.destination,
                "destination_label": "Vitrina" if p.destination == "VITRINA" else ("Cabina" if p.destination == "CABINA" else p.get_destination_display()),
                "taxable_amount": f"{p.taxable_amount:.2f}",
                "exempt_amount": f"{p.exempt_amount:.2f}",
                "iva_credit": f"{p.iva_credit:.2f}",
                "iva_perceived": f"{p.iva_perceived:.2f}",
                "total": f"{p.total:.2f}",
                "payment_condition": p.payment_condition,
                "due_date": p.due_date.isoformat() if p.due_date else None,
                "amount_paid": f"{p.amount_paid:.2f}",
                "balance_due": f"{balance_due:.2f}",
                "payment_status": p.payment_status,
                "payment_status_label": p.get_payment_status_display(),
                "status": p.status,
                "void_reason": p.void_reason or "",
                "journal_entry_id": p.journal_entry_id,
                "journal_entry_number": p.journal_entry.entry_number if p.journal_entry else None,
                "notes": p.notes or "",
                "lines": [
                    {
                        "id": ln.id,
                        "line_no": ln.line_no,
                        "product_id": ln.product_id,
                        "product_sku": ln.product.sku if ln.product else "",
                        "location_name": ln.location.name if ln.location else "",
                        "description": ln.description,
                        "quantity": f"{ln.quantity:.2f}",
                        "unit_cost": f"{ln.unit_cost:.2f}",
                        "taxable_amount": f"{ln.taxable_amount:.2f}",
                        "iva_amount": f"{ln.iva_amount:.2f}",
                    }
                    for ln in p.lines.all()
                ],
            }
        )

    # Withholdings & Perceptions report (RF-COM-10)
    from apps.sales.models import Sale

    sales_withheld = (
        Sale.objects.filter(period=period_obj, status="ISSUED", iva_withheld__gt=0)
        if period_obj
        else Sale.objects.filter(status="ISSUED", iva_withheld__gt=0)
    )
    total_sales_withheld = sum((s.iva_withheld for s in sales_withheld), Decimal("0.00"))

    return {
        "period": {
            "id": period_obj.id if period_obj else None,
            "label": period_obj.label if period_obj else "Noviembre 2026",
        },
        "kpis": {
            "total_purchases": f"{total_amount:.2f}",
            "taxable_base": f"{total_taxable:.2f}",
            "iva_credit": f"{total_iva:.2f}",
            "iva_perceived": f"{total_perceived:.2f}",
            "active_suppliers_count": len(active_suppliers),
            "active_suppliers_names": supplier_names_summary,
            "documents_count": len(active_purchases),
        },
        "distribution": {
            "vitrina_amount": f"{vit_total:.2f}",
            "vitrina_pct": vit_pct,
            "cabina_amount": f"{cab_total:.2f}",
            "cabina_pct": cab_pct,
            "expense_amount": f"{exp_total:.2f}",
        },
        "purchases": rows,
        "totals": {
            "taxable_amount": f"{total_taxable:.2f}",
            "exempt_amount": f"{total_exempt:.2f}",
            "iva_credit": f"{total_iva:.2f}",
            "iva_perceived": f"{total_perceived:.2f}",
            "total": f"{total_amount:.2f}",
        },
        "withholdings": {
            "iva_credit_13": f"{total_iva:.2f}",
            "iva_perceived_1": f"{total_perceived:.2f}",
            "iva_withheld_sales_1": f"{total_sales_withheld:.2f}",
            "total_acreditable": f"{(total_iva + total_perceived + total_sales_withheld):.2f}",
        },
    }
