from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.accounting.models import JournalEntry
from apps.accounting.services.posting import LineDTO, get_account, post_entry
from apps.core.models import AuditLog, Company, Employee
from apps.core.services.audit import log_audit, serialize_instance
from apps.core.services.periods import get_open_period
from apps.inventory.models import (
    Adjustment,
    Category,
    Consumption,
    InventoryMovement,
    Location,
    Product,
    Stock,
)


class InsufficientStockError(ValidationError):
    """Raised when an outgoing movement would make stock negative (RF-INV-11)."""


class RegimeMismatchError(ValidationError):
    """Raised when Vitrina and Cabina regimes are mixed illegally (RN-07)."""


Q2 = Decimal("0.01")
Q3 = Decimal("0.001")
Q4 = Decimal("0.0001")

INCOMING_TYPES = {
    InventoryMovement.MovementType.OPENING,
    InventoryMovement.MovementType.PURCHASE,
    InventoryMovement.MovementType.ADJUSTMENT_IN,
    InventoryMovement.MovementType.TRANSFER_IN,
    InventoryMovement.MovementType.RETURN_IN,
}

OUTGOING_TYPES = {
    InventoryMovement.MovementType.SALE,
    InventoryMovement.MovementType.CONSUMPTION,
    InventoryMovement.MovementType.ADJUSTMENT_OUT,
    InventoryMovement.MovementType.TRANSFER_OUT,
    InventoryMovement.MovementType.RETURN_OUT,
}


def _coerce_date(val: date | datetime | str) -> date:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return date.fromisoformat(str(val)[:10])


def _resolve_product(product: Product | int | str) -> Product:
    if isinstance(product, Product):
        return Product.objects.select_for_update().get(pk=product.pk)
    if isinstance(product, int) or (isinstance(product, str) and product.isdigit()):
        prod = Product.objects.select_for_update().filter(pk=int(product)).first()
        if prod:
            return prod
    prod = Product.objects.select_for_update().filter(sku=str(product)).first()
    if not prod:
        raise ValidationError(f"Producto de inventario «{product}» no encontrado.")
    return prod


def _resolve_location(location: Location | int | str | None, *, default_for_regime: str | None = None) -> Location:
    if isinstance(location, Location):
        return location
    if isinstance(location, int) or (isinstance(location, str) and location.isdigit()):
        loc = Location.objects.filter(pk=int(location), is_active=True).first()
        if loc:
            return loc
    if isinstance(location, str) and location.strip():
        key = location.strip().upper()
        loc = (
            Location.objects.filter(code__iexact=key, is_active=True).first()
            or Location.objects.filter(location_type__iexact=key, is_active=True).order_by("id").first()
            or Location.objects.filter(name__iexact=key, is_active=True).first()
        )
        if loc:
            return loc
    if default_for_regime == Product.InventoryType.VITRINA:
        loc = Location.objects.filter(location_type=Location.LocationType.VITRINA, is_active=True).first()
        if loc:
            return loc
    elif default_for_regime == Product.InventoryType.CABINA:
        loc = Location.objects.filter(location_type=Location.LocationType.CABINA, is_active=True).first()
        if loc:
            return loc
    loc = Location.objects.filter(is_active=True).order_by("id").first()
    if not loc:
        raise ValidationError("No existe una ubicación de inventario activa.")
    return loc


@transaction.atomic
def register_movement(
    *,
    product: Product | int | str,
    location: Location | int | str | None = None,
    movement_type: str,
    quantity: Decimal | int | float | str,
    unit_cost: Decimal | int | float | str | None = None,
    movement_date: date | str,
    source_app: str | None = None,
    source_id: int | None = None,
    journal_entry: JournalEntry | None = None,
    notes: str | None = None,
    user,
) -> InventoryMovement:
    """
    Core Kárdex & Weighted-Average Cost engine (DB_DESIGN.md §6, RF-INV-05..07, RF-INV-11, RN-07).
    Updates Stock at location, recomputes Product.average_cost on incoming purchases/openings,
    and appends an immutable InventoryMovement record.
    """
    m_date = _coerce_date(movement_date)
    prod = _resolve_product(product)
    loc = _resolve_location(location, default_for_regime=prod.inventory_type)

    qty = Decimal(str(quantity)).quantize(Q3, rounding=ROUND_HALF_UP)
    if qty <= Decimal("0.000"):
        raise ValidationError("La cantidad del movimiento de inventario debe ser mayor a cero.")

    m_type = str(movement_type).upper()
    if m_type not in INCOMING_TYPES and m_type not in OUTGOING_TYPES:
        raise ValidationError(f"Tipo de movimiento de Kárdex inválido: {m_type}")

    # Enforce RN-07: Vitrina and Cabina never mix
    if prod.inventory_type == Product.InventoryType.VITRINA:
        if loc.location_type == Location.LocationType.CABINA:
            raise RegimeMismatchError(
                f"RN-07: El producto de Vitrina «{prod.name}» no puede ubicarse en la estación «{loc.name}»."
            )
        if m_type == InventoryMovement.MovementType.CONSUMPTION:
            raise RegimeMismatchError(
                f"RN-07: El producto de Vitrina «{prod.name}» está destinado a la venta y no puede consumirse en cabina sin reclasificarse."
            )
    elif prod.inventory_type == Product.InventoryType.CABINA:
        if loc.location_type == Location.LocationType.VITRINA:
            raise RegimeMismatchError(
                f"RN-07: El insumo de Cabina «{prod.name}» no puede ubicarse en Vitrina comercial."
            )
        if m_type == InventoryMovement.MovementType.SALE:
            raise RegimeMismatchError(
                f"RN-07: El insumo de Cabina «{prod.name}» es de uso técnico y no puede venderse directamente."
            )

    direction = 1 if m_type in INCOMING_TYPES else -1

    # Total product stock across all locations BEFORE movement
    total_qty_before = (
        Stock.objects.select_for_update()
        .filter(product=prod)
        .aggregate(s=models.Sum("quantity"))["s"]
        or Decimal("0.000")
    )

    stock_row, _ = Stock.objects.select_for_update().get_or_create(
        product=prod,
        location=loc,
        defaults={"quantity": Decimal("0.000")},
    )

    if direction == -1:
        # Check negative stock (RF-INV-11)
        company = Company.objects.first()
        allow_neg = bool(getattr(company, "allow_negative_stock", False))
        if stock_row.quantity < qty and not allow_neg:
            raise InsufficientStockError(
                f"Stock insuficiente de «{prod.name}» en {loc.name} "
                f"(disponible: {stock_row.quantity}, requerido: {qty})."
            )
        eff_unit_cost = (
            Decimal(str(unit_cost)).quantize(Q4, rounding=ROUND_HALF_UP)
            if unit_cost is not None
            else prod.average_cost
        )
        new_avg_cost = prod.average_cost
        new_loc_qty = (stock_row.quantity - qty).quantize(Q3)
        new_total_qty = max(Decimal("0.000"), (total_qty_before - qty).quantize(Q3))
    else:
        eff_unit_cost = (
            Decimal(str(unit_cost)).quantize(Q4, rounding=ROUND_HALF_UP)
            if unit_cost is not None
            else prod.average_cost
        )
        new_loc_qty = (stock_row.quantity + qty).quantize(Q3)
        new_total_qty = (total_qty_before + qty).quantize(Q3)

        # Recompute weighted-average cost on OPENING and PURCHASE (RF-INV-07)
        if m_type in (InventoryMovement.MovementType.OPENING, InventoryMovement.MovementType.PURCHASE):
            if new_total_qty > Decimal("0.000"):
                prev_val = total_qty_before * prod.average_cost
                in_val = qty * eff_unit_cost
                new_avg_cost = ((prev_val + in_val) / new_total_qty).quantize(Q4, rounding=ROUND_HALF_UP)
            else:
                new_avg_cost = eff_unit_cost
        elif total_qty_before <= Decimal("0.000") and eff_unit_cost > Decimal("0.0000"):
            new_avg_cost = eff_unit_cost
        else:
            new_avg_cost = prod.average_cost

    total_cost = (qty * eff_unit_cost).quantize(Q2, rounding=ROUND_HALF_UP)

    stock_row.quantity = new_loc_qty
    stock_row.save(update_fields=["quantity"])

    if prod.average_cost != new_avg_cost:
        prod.average_cost = new_avg_cost
        prod.save(update_fields=["average_cost", "updated_at"])

    movement = InventoryMovement.objects.create(
        product=prod,
        location=loc,
        movement_date=m_date,
        movement_type=m_type,
        direction=direction,
        quantity=qty,
        unit_cost=eff_unit_cost,
        total_cost=total_cost,
        balance_quantity=new_total_qty,
        balance_avg_cost=new_avg_cost,
        source_app=source_app,
        source_id=source_id,
        journal_entry=journal_entry,
        notes=notes or "",
        created_by=user,
    )
    return movement


@transaction.atomic
def create_adjustment(
    *,
    adjustment_date: date | str,
    reason: str,
    lines: list[dict],
    notes: str = "",
    user,
) -> Adjustment:
    """
    Create a stock adjustment (physical count, damage, expiry, theft) and post its
    journal entry against Faltantes (420102) or Sobrantes (5201) (RF-INV-08).
    Each line dict: {product_id, location_id, direction ('IN'|'OUT' or +1|-1), quantity, notes?}
    """
    a_date = _coerce_date(adjustment_date)
    get_open_period(a_date)

    if not lines:
        raise ValidationError("El ajuste de stock debe incluir al menos un producto.")

    adj = Adjustment.objects.create(
        adjustment_date=a_date,
        reason=reason,
        notes=notes or "",
        created_by=user,
    )

    movements: list[InventoryMovement] = []
    entry_lines: list[LineDTO] = []

    for raw in lines:
        prod = _resolve_product(raw.get("product_id") or raw.get("product"))
        loc = _resolve_location(
            raw.get("location_id") or raw.get("location"),
            default_for_regime=prod.inventory_type,
        )
        raw_dir = str(raw.get("direction", "OUT")).upper()
        is_in = raw_dir in ("IN", "1", "+1", "ADJUSTMENT_IN", "SOBRANTE")
        m_type = (
            InventoryMovement.MovementType.ADJUSTMENT_IN
            if is_in
            else InventoryMovement.MovementType.ADJUSTMENT_OUT
        )
        qty = Decimal(str(raw.get("quantity", 0)))

        mov = register_movement(
            product=prod,
            location=loc,
            movement_type=m_type,
            quantity=qty,
            unit_cost=prod.average_cost,
            movement_date=a_date,
            source_app="inventory.adjustment",
            source_id=adj.pk,
            notes=raw.get("notes") or notes or f"Ajuste ({adj.get_reason_display()})",
            user=user,
        )
        movements.append(mov)

        inv_key = (
            "INVENTORY_VITRINA"
            if prod.inventory_type == Product.InventoryType.VITRINA
            else "INVENTORY_CABINA"
        )
        if mov.total_cost > Decimal("0.00"):
            if is_in:
                entry_lines.append(
                    LineDTO(
                        account=get_account(inv_key),
                        debit=mov.total_cost,
                        description=f"Sobrante inventario {prod.name} ({loc.name})",
                    )
                )
                entry_lines.append(
                    LineDTO(
                        account=get_account("INVENTORY_SURPLUS"),
                        credit=mov.total_cost,
                        description=f"Ingreso por sobrante de inventario ({adj.get_reason_display()})",
                    )
                )
            else:
                entry_lines.append(
                    LineDTO(
                        account=get_account("INVENTORY_SHORTAGE"),
                        debit=mov.total_cost,
                        description=f"Gasto por faltante/merma {prod.name} ({adj.get_reason_display()})",
                    )
                )
                entry_lines.append(
                    LineDTO(
                        account=get_account(inv_key),
                        credit=mov.total_cost,
                        description=f"Descargo inventario {prod.name} ({loc.name})",
                    )
                )

    if entry_lines:
        j_entry = post_entry(
            entry_date=a_date,
            description=f"Ajuste de inventario #{adj.pk} ({adj.get_reason_display()}) — {notes or 'Conteo físico'}",
            lines=entry_lines,
            entry_type=JournalEntry.EntryType.ADJUSTMENT,
            source_app="inventory.adjustment",
            source_id=adj.pk,
            user=user,
        )
        adj.journal_entry = j_entry
        adj.save(update_fields=["journal_entry"])
        InventoryMovement.objects.filter(pk__in=[m.pk for m in movements]).update(journal_entry=j_entry)

    log_audit(
        user=user,
        action=AuditLog.Action.CREATE,
        table_name="inventory_adjustment",
        record_id=adj.pk,
        after_data=serialize_instance(adj),
    )
    return adj


@transaction.atomic
def register_consumption(
    *,
    consumption_date: date | str,
    location: Location | int | str,
    lines: list[dict],
    employee: Employee | int | None = None,
    sale_id: int | None = None,
    notes: str = "",
    user,
) -> Consumption:
    """
    Record Cabina supply consumption per station and day, posting
    Dr 410201 Costo de insumos de servicios / Cr 110502 Insumos para servicios (cabina) (RF-INV-09).
    """
    c_date = _coerce_date(consumption_date)
    get_open_period(c_date)

    loc = _resolve_location(location, default_for_regime=Product.InventoryType.CABINA)
    if loc.location_type == Location.LocationType.VITRINA:
        raise RegimeMismatchError("El consumo técnico de insumos solo puede registrarse desde Cabina o Bodega General.")

    if not lines:
        raise ValidationError("Debe indicar al menos un insumo de cabina consumido.")

    emp_obj = None
    if isinstance(employee, Employee):
        emp_obj = employee
    elif employee:
        emp_obj = Employee.objects.filter(pk=int(employee)).first()

    cons = Consumption.objects.create(
        consumption_date=c_date,
        location=loc,
        employee=emp_obj,
        sale_id=sale_id,
        notes=notes or "",
        created_by=user,
    )

    movements: list[InventoryMovement] = []
    total_cost = Decimal("0.00")

    for raw in lines:
        prod = _resolve_product(raw.get("product_id") or raw.get("product"))
        if prod.inventory_type != Product.InventoryType.CABINA:
            raise RegimeMismatchError(
                f"RN-07: El producto «{prod.name}» pertenece a Vitrina y no puede consumirse en Cabina."
            )
        line_loc = _resolve_location(
            raw.get("location_id") or raw.get("location") or loc,
            default_for_regime=Product.InventoryType.CABINA,
        )
        qty = Decimal(str(raw.get("quantity", 0)))

        mov = register_movement(
            product=prod,
            location=line_loc,
            movement_type=InventoryMovement.MovementType.CONSUMPTION,
            quantity=qty,
            unit_cost=prod.average_cost,
            movement_date=c_date,
            source_app="inventory.consumption",
            source_id=cons.pk,
            notes=notes or f"Consumo en {line_loc.name}",
            user=user,
        )
        movements.append(mov)
        total_cost += mov.total_cost

    if total_cost > Decimal("0.00"):
        j_entry = post_entry(
            entry_date=c_date,
            description=f"Consumo de insumos en {loc.name} #{cons.pk} — {notes or 'Servicios de estación'}",
            lines=[
                LineDTO(
                    account=get_account("SERVICE_SUPPLY_COST"),
                    debit=total_cost,
                    description=f"Aplicación de insumos técnicos en {loc.name}",
                ),
                LineDTO(
                    account=get_account("INVENTORY_CABINA"),
                    credit=total_cost,
                    description=f"Descargo de inventario de insumos Cabina ({loc.name})",
                ),
            ],
            entry_type=JournalEntry.EntryType.INVENTORY,
            source_app="inventory.consumption",
            source_id=cons.pk,
            user=user,
        )
        cons.journal_entry = j_entry
        cons.save(update_fields=["journal_entry"])
        InventoryMovement.objects.filter(pk__in=[m.pk for m in movements]).update(journal_entry=j_entry)

    log_audit(
        user=user,
        action=AuditLog.Action.CREATE,
        table_name="inventory_consumption",
        record_id=cons.pk,
        after_data=serialize_instance(cons),
    )
    return cons


@transaction.atomic
def transfer_stock(
    *,
    transfer_date: date | str,
    product: Product | int | str,
    from_location: Location | int | str,
    to_location: Location | int | str,
    quantity: Decimal | int | float | str,
    target_product: Product | int | str | None = None,
    notes: str = "",
    user,
) -> dict:
    """
    Transfer stock between locations (e.g. Bodega General -> Cabina 1) or reclassify
    between regimes (Vitrina <-> Cabina) with automatic journal entry (RF-INV-12).
    """
    t_date = _coerce_date(transfer_date)
    get_open_period(t_date)

    src_prod = _resolve_product(product)
    src_loc = _resolve_location(from_location, default_for_regime=src_prod.inventory_type)
    dst_loc = _resolve_location(to_location)
    qty = Decimal(str(quantity)).quantize(Q3, rounding=ROUND_HALF_UP)

    if target_product:
        dst_prod = _resolve_product(target_product)
    else:
        dst_prod = src_prod

    if src_prod.pk == dst_prod.pk and src_loc.pk == dst_loc.pk:
        raise ValidationError("La ubicación de origen y destino deben ser distintas.")

    # 1. Outgoing movement from source
    mov_out = register_movement(
        product=src_prod,
        location=src_loc,
        movement_type=InventoryMovement.MovementType.TRANSFER_OUT,
        quantity=qty,
        unit_cost=src_prod.average_cost,
        movement_date=t_date,
        source_app="inventory.transfer",
        source_id=src_prod.pk,
        notes=notes or f"Transferencia hacia {dst_loc.name}",
        user=user,
    )

    # 2. Incoming movement into destination
    mov_in = register_movement(
        product=dst_prod,
        location=dst_loc,
        movement_type=InventoryMovement.MovementType.TRANSFER_IN,
        quantity=qty,
        unit_cost=mov_out.unit_cost,
        movement_date=t_date,
        source_app="inventory.transfer",
        source_id=dst_prod.pk,
        notes=notes or f"Transferencia desde {src_loc.name}",
        user=user,
    )

    j_entry = None
    if src_prod.inventory_type != dst_prod.inventory_type and mov_out.total_cost > Decimal("0.00"):
        j_entry = post_entry(
            entry_date=t_date,
            description=f"Reclasificación de inventario {src_prod.sku} ({src_prod.inventory_type}) → {dst_prod.sku} ({dst_prod.inventory_type})",
            lines=[
                LineDTO(
                    account=dst_prod.account,
                    debit=mov_out.total_cost,
                    description=f"Ingreso por reclasificación a {dst_prod.name}",
                ),
                LineDTO(
                    account=src_prod.account,
                    credit=mov_out.total_cost,
                    description=f"Salida por reclasificación desde {src_prod.name}",
                ),
            ],
            entry_type=JournalEntry.EntryType.INVENTORY,
            source_app="inventory.transfer",
            source_id=mov_out.pk,
            user=user,
        )
        InventoryMovement.objects.filter(pk__in=[mov_out.pk, mov_in.pk]).update(journal_entry=j_entry)

    return {
        "movement_out_id": mov_out.pk,
        "movement_in_id": mov_in.pk,
        "total_cost": str(mov_out.total_cost),
        "journal_entry_id": j_entry.pk if j_entry else None,
    }


def _unit_short(uom: str) -> str:
    mapping = {
        "UNIT": "u",
        "LITER": "L",
        "MILLILITER": "ml",
        "GRAM": "g",
        "KILOGRAM": "kg",
        "PACKAGE": "paq",
    }
    return mapping.get(uom, "u")


def get_inventory_summary(*, search_vitrina: str = "", search_cabina: str = "", location: str = "") -> dict:
    """
    Build complete payload for Vista 2 · Inventario Mixto (RF-INV-01..03) matching the
    reference mock-up (dual Vitrina/Cabina panels, KPI cards, and critical stock alert).
    """
    products = (
        Product.objects.filter(is_active=True)
        .select_related("category", "account", "default_supplier")
        .prefetch_related("stocks__location")
        .order_by("id")
    )

    vitrina_items = []
    cabina_items = []
    critical_items = []

    vitrina_total_units = Decimal("0.000")
    vitrina_cost_valuation = Decimal("0.00")
    vitrina_pvp_valuation = Decimal("0.00")

    cabina_total_units = Decimal("0.000")
    cabina_cost_valuation = Decimal("0.00")

    for p in products:
        stocks = [s for s in p.stocks.all() if s.quantity > 0]
        if location:
            stocks_filtered = [
                s for s in stocks if s.location.code.upper() == location.upper() or str(s.location_id) == str(location)
            ]
        else:
            stocks_filtered = stocks

        total_qty = sum((s.quantity for s in stocks), Decimal("0.000"))
        primary_loc = stocks[0].location.name if stocks else ("Vitrina" if p.inventory_type == "VITRINA" else "General")
        primary_loc_code = stocks[0].location.code if stocks else ("VIT" if p.inventory_type == "VITRINA" else "GEN")
        primary_loc_id = stocks[0].location_id if stocks else None

        cost_val = (total_qty * p.average_cost).quantize(Q2, rounding=ROUND_HALF_UP)
        pvp_val = (total_qty * (p.sale_price or Decimal("0.00"))).quantize(Q2, rounding=ROUND_HALF_UP)
        is_critical = total_qty <= p.min_stock

        item_dict = {
            "id": p.id,
            "sku": p.sku,
            "barcode": p.barcode or "",
            "name": p.name,
            "brand": p.brand or "",
            "presentation": p.presentation or "",
            "category_id": p.category_id,
            "category_name": p.category.name if p.category else "",
            "inventory_type": p.inventory_type,
            "unit_of_measure": p.unit_of_measure,
            "unit_short": _unit_short(p.unit_of_measure),
            "account_code": p.account.code,
            "quantity": str(total_qty),
            "quantity_display": f"{int(total_qty) if total_qty == int(total_qty) else total_qty} {_unit_short(p.unit_of_measure)}",
            "sale_price": f"{p.sale_price:.2f}" if p.sale_price is not None else None,
            "average_cost": f"{p.average_cost:.4f}",
            "cost_valuation": f"{cost_val:.2f}",
            "pvp_valuation": f"{pvp_val:.2f}",
            "min_stock": str(p.min_stock),
            "is_critical": is_critical,
            "location_name": primary_loc,
            "location_code": primary_loc_code,
            "location_id": primary_loc_id,
            "classification_badge": "Venta" if p.inventory_type == "VITRINA" else "Servicio",
            "default_supplier_id": p.default_supplier_id,
            "default_supplier_name": p.default_supplier.name if p.default_supplier else "",
            "stocks_by_location": [
                {
                    "location_id": s.location_id,
                    "location_code": s.location.code,
                    "location_name": s.location.name,
                    "quantity": str(s.quantity),
                }
                for s in stocks
            ],
        }

        if is_critical:
            critical_items.append(item_dict)

        if p.inventory_type == Product.InventoryType.VITRINA:
            vitrina_total_units += total_qty
            vitrina_cost_valuation += cost_val
            vitrina_pvp_valuation += pvp_val
            if search_vitrina:
                q = search_vitrina.lower().strip()
                if q not in p.name.lower() and q not in (p.brand or "").lower() and q not in p.sku.lower():
                    continue
            if location and not stocks_filtered:
                continue
            vitrina_items.append(item_dict)
        else:
            cabina_total_units += total_qty
            cabina_cost_valuation += cost_val
            if search_cabina:
                q = search_cabina.lower().strip()
                if (
                    q not in p.name.lower()
                    and q not in (p.brand or "").lower()
                    and q not in p.sku.lower()
                    and q not in primary_loc.lower()
                ):
                    continue
            if location and not stocks_filtered:
                continue
            cabina_items.append(item_dict)

    active_stations = Location.objects.filter(is_active=True).count()

    # Build critical alert summary label (e.g. "Acondicionador & Serum")
    crit_short_names = []
    for ci in critical_items:
        first_word = ci["name"].split()[0].capitalize()
        if first_word not in crit_short_names:
            crit_short_names.append(first_word)
    crit_label = " & ".join(reversed(crit_short_names[:2])) if crit_short_names else "Stock óptimo"

    return {
        "kpis": {
            "vitrina": {
                "items_count": len(vitrina_items),
                "units_total": f"{int(vitrina_total_units) if vitrina_total_units == int(vitrina_total_units) else vitrina_total_units}",
                "cost_valuation": f"{vitrina_cost_valuation:.2f}",
                "pvp_valuation": f"{vitrina_pvp_valuation:.2f}",
                "account_code": "1104-01",
            },
            "cabina": {
                "items_count": len(cabina_items),
                "units_total": f"{int(cabina_total_units) if cabina_total_units == int(cabina_total_units) else cabina_total_units}",
                "cost_valuation": f"{cabina_cost_valuation:.2f}",
                "active_stations": active_stations,
                "account_code": "1104-02",
            },
            "critical": {
                "count": len(critical_items),
                "suggested_restock": crit_label,
                "items": critical_items,
            },
        },
        "vitrina_items": vitrina_items,
        "cabina_items": cabina_items,
        "locations": [
            {"id": loc.id, "code": loc.code, "name": loc.name, "location_type": loc.location_type}
            for loc in Location.objects.filter(is_active=True).order_by("id")
        ],
        "categories": [
            {"id": cat.id, "name": cat.name, "inventory_type": cat.inventory_type}
            for cat in Category.objects.all()
        ],
    }


def get_product_kardex(
    product_id: int,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    prod = Product.objects.select_related("account", "category").get(pk=product_id)
    qs = (
        InventoryMovement.objects.filter(product=prod)
        .select_related("location", "journal_entry", "created_by")
        .order_by("movement_date", "id")
    )
    if date_from:
        qs = qs.filter(movement_date__gte=_coerce_date(date_from))
    if date_to:
        qs = qs.filter(movement_date__lte=_coerce_date(date_to))

    movements = [
        {
            "id": m.id,
            "movement_date": m.movement_date.isoformat(),
            "movement_type": m.movement_type,
            "movement_type_label": m.get_movement_type_display(),
            "direction": m.direction,
            "location_code": m.location.code,
            "location_name": m.location.name,
            "quantity": f"{m.quantity:.3f}",
            "unit_cost": f"{m.unit_cost:.4f}",
            "total_cost": f"{m.total_cost:.2f}",
            "balance_quantity": f"{m.balance_quantity:.3f}",
            "balance_avg_cost": f"{m.balance_avg_cost:.4f}",
            "balance_valuation": f"{(m.balance_quantity * m.balance_avg_cost).quantize(Q2):.2f}",
            "journal_entry_id": m.journal_entry_id,
            "journal_entry_number": m.journal_entry.entry_number if m.journal_entry else None,
            "notes": m.notes or "",
        }
        for m in qs
    ]

    total_qty = (
        Stock.objects.filter(product=prod).aggregate(s=models.Sum("quantity"))["s"] or Decimal("0.000")
    )

    return {
        "product": {
            "id": prod.id,
            "sku": prod.sku,
            "name": prod.name,
            "brand": prod.brand or "",
            "inventory_type": prod.inventory_type,
            "account_code": prod.account.code,
            "current_stock": f"{total_qty:.3f}",
            "average_cost": f"{prod.average_cost:.4f}",
            "total_valuation": f"{(total_qty * prod.average_cost).quantize(Q2):.2f}",
        },
        "movements": movements,
    }
