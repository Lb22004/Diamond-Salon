import calendar
from collections.abc import Iterable
from datetime import date, datetime

from django.apps import apps as django_apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import BooleanField, Exists, ExpressionWrapper, OuterRef, ProtectedError, QuerySet, Value

from apps.core.exceptions import ClosedPeriodError
from apps.core.models import AccountingPeriod, FiscalYear, PeriodStatus, User
from apps.core.services.audit import log_audit, serialize_instance


def _coerce_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise ValidationError("Fecha inválida para determinar el período contable.")


def get_open_period(entry_date: date | datetime | str) -> AccountingPeriod:
    """Return the OPEN AccountingPeriod covering ``entry_date`` or raise ``ClosedPeriodError``.

    Cross-module service contract defined in DB_DESIGN.md §6 and SRS RN-03:
      - Raises ``ClosedPeriodError("El período MM/YYYY está cerrado")`` if closed.
      - Raises ``ClosedPeriodError`` if no period exists for the given date.
    """
    target_date = _coerce_date(entry_date)
    period = (
        AccountingPeriod.objects.select_related("fiscal_year")
        .filter(start_date__lte=target_date, end_date__gte=target_date)
        .first()
    )
    if period is None:
        period = (
            AccountingPeriod.objects.select_related("fiscal_year")
            .filter(year=target_date.year, month=target_date.month)
            .first()
        )

    if period is None:
        raise ClosedPeriodError(
            f"No existe un período contable configurado para {target_date.month:02d}/{target_date.year}"
        )

    if period.status != PeriodStatus.OPEN or period.fiscal_year.status != PeriodStatus.OPEN:
        raise ClosedPeriodError(f"El período {period.month:02d}/{period.year} está cerrado")

    return period


def get_active_period() -> AccountingPeriod | None:
    """Return the currently active working period in the UI (RF-CIE-01)."""
    active = AccountingPeriod.objects.select_related("fiscal_year").filter(is_active=True).first()
    if active:
        return active
    return (
        AccountingPeriod.objects.select_related("fiscal_year")
        .filter(status=PeriodStatus.OPEN)
        .order_by("-year", "-month")
        .first()
    )


@transaction.atomic
def activate_period(period: AccountingPeriod, *, user: User | None = None) -> AccountingPeriod:
    """Set ``period`` as the single active working period in the system."""
    before = serialize_instance(period)
    AccountingPeriod.objects.exclude(pk=period.pk).filter(is_active=True).update(is_active=False)
    if not period.is_active or period.is_hidden:
        # The active period must always be visible in the selector.
        period.is_active = True
        period.is_hidden = False
        period.save(update_fields=["is_active", "is_hidden"])
    log_audit(
        action="UPDATE",
        table_name="core_accounting_period",
        record_id=period.pk,
        before_data=before,
        after_data=serialize_instance(period),
        user=user,
    )
    return period


@transaction.atomic
def generate_periods(
    year: int,
    months: Iterable[int] | None = None,
    *,
    user: User | None = None,
) -> tuple[FiscalYear, list[AccountingPeriod]]:
    """Generate the FiscalYear ``year`` and the requested monthly periods (RF-CIE-01).

    ``months=None`` generates the full year (1..12). Already existing months are skipped,
    so the operation is idempotent and can be used to fill a partial year month by month.
    Returns the fiscal year and the list of newly created periods.
    """
    if year < 2000 or year > 2100:
        raise ValidationError("El año fiscal debe estar entre 2000 y 2100.")

    if months is None:
        target_months = list(range(1, 13))
    else:
        try:
            target_months = sorted({int(m) for m in months})
        except (TypeError, ValueError) as exc:
            raise ValidationError("Los meses indicados no son válidos.") from exc
        if not target_months:
            raise ValidationError("Debe seleccionar al menos un mes a generar.")
        if any(m < 1 or m > 12 for m in target_months):
            raise ValidationError("Los meses deben estar entre 1 y 12.")

    fy, fy_created = FiscalYear.objects.get_or_create(
        year=year,
        defaults={
            "start_date": date(year, 1, 1),
            "end_date": date(year, 12, 31),
            "status": PeriodStatus.OPEN,
        },
    )
    if fy_created:
        log_audit(
            action="CREATE",
            table_name="core_fiscal_year",
            record_id=fy.pk,
            after_data=serialize_instance(fy),
            user=user,
        )

    has_any_active = AccountingPeriod.objects.filter(is_active=True).exists()
    created_periods: list[AccountingPeriod] = []
    for month in target_months:
        last_day = calendar.monthrange(year, month)[1]
        make_active = not has_any_active
        period, p_created = AccountingPeriod.objects.get_or_create(
            year=year,
            month=month,
            defaults={
                "fiscal_year": fy,
                "start_date": date(year, month, 1),
                "end_date": date(year, month, last_day),
                "status": PeriodStatus.OPEN,
                "is_active": make_active,
            },
        )
        if not p_created:
            continue
        if make_active:
            has_any_active = True
        created_periods.append(period)
        log_audit(
            action="CREATE",
            table_name="core_accounting_period",
            record_id=period.pk,
            after_data=serialize_instance(period),
            user=user,
        )

    return fy, created_periods


def generate_fiscal_year_periods(
    year: int,
    *,
    months: Iterable[int] | None = None,
    user: User | None = None,
) -> FiscalYear:
    """Generate a FiscalYear and its monthly AccountingPeriod rows (all 12 by default)."""
    fy, _ = generate_periods(year, months, user=user)
    return fy


def generate_next_period(*, user: User | None = None) -> AccountingPeriod:
    """Create the month immediately after the latest existing period (rolls into a new year)."""
    latest = AccountingPeriod.objects.order_by("-year", "-month").first()
    if latest is None:
        today = date.today()
        year, month = today.year, today.month
    elif latest.month == 12:
        year, month = latest.year + 1, 1
    else:
        year, month = latest.year, latest.month + 1

    _, created = generate_periods(year, [month], user=user)
    if created:
        return created[0]
    return AccountingPeriod.objects.get(year=year, month=month)


# ---------------------------------------------------------------------------
# Usage detection (what counts as "registered data" in a period)
# ---------------------------------------------------------------------------

# (label, app_label.ModelName, lookup) — FK-based references to AccountingPeriod.
_PERIOD_FK_USAGE = (
    ("journal_entries", "accounting.JournalEntry", "period"),
    ("period_balances", "accounting.PeriodBalance", "period"),
    ("sales", "sales.Sale", "period"),
    ("purchases", "purchases.Purchase", "period"),
)
# (label, app_label.ModelName, date_field) — date-based records without a period FK.
_PERIOD_DATE_USAGE = (("inventory_movements", "inventory.InventoryMovement", "movement_date"),)

USAGE_LABELS_ES = {
    "journal_entries": "partida(s)",
    "period_balances": "saldo(s) de cierre",
    "sales": "venta(s)",
    "purchases": "compra(s)",
    "inventory_movements": "movimiento(s) de inventario",
}


def _get_model(dotted: str):
    try:
        return django_apps.get_model(dotted)
    except LookupError:
        return None


def period_usage(period: AccountingPeriod) -> dict[str, int]:
    """Return counts of every record type linked to ``period``."""
    usage: dict[str, int] = {}
    for label, dotted, lookup in _PERIOD_FK_USAGE:
        model = _get_model(dotted)
        usage[label] = model.objects.filter(**{lookup: period}).count() if model else 0
    for label, dotted, date_field in _PERIOD_DATE_USAGE:
        model = _get_model(dotted)
        usage[label] = (
            model.objects.filter(
                **{f"{date_field}__gte": period.start_date, f"{date_field}__lte": period.end_date}
            ).count()
            if model
            else 0
        )
    return usage


def annotate_has_data(queryset: QuerySet) -> QuerySet:
    """Annotate an AccountingPeriod queryset with a boolean ``has_data`` (no N+1 queries)."""
    conditions = []
    for _label, dotted, lookup in _PERIOD_FK_USAGE:
        model = _get_model(dotted)
        if model:
            conditions.append(Exists(model.objects.filter(**{lookup: OuterRef("pk")})))
    for _label, dotted, date_field in _PERIOD_DATE_USAGE:
        model = _get_model(dotted)
        if model:
            conditions.append(
                Exists(
                    model.objects.filter(
                        **{
                            f"{date_field}__gte": OuterRef("start_date"),
                            f"{date_field}__lte": OuterRef("end_date"),
                        }
                    )
                )
            )
    if not conditions:
        return queryset.annotate(has_data=Value(False, output_field=BooleanField()))
    combined = conditions[0]
    for cond in conditions[1:]:
        combined = combined | cond
    return queryset.annotate(has_data=ExpressionWrapper(combined, output_field=BooleanField()))


def _describe_usage(usage: dict[str, int]) -> str:
    return ", ".join(f"{count} {USAGE_LABELS_ES.get(k, k)}" for k, count in usage.items() if count)


def _require_admin(user: User | None, action: str) -> None:
    if not user or not (user.role == User.Role.ADMIN or user.is_superuser):
        raise ValidationError(f"Solo un usuario con rol ADMIN puede {action}.")


def can_delete_period(period: AccountingPeriod) -> tuple[bool, str | None]:
    """Check whether ``period`` can be safely deleted (OPEN and without any registered data)."""
    if period.status != PeriodStatus.OPEN:
        return False, f"El período {period.code} está cerrado y no puede eliminarse."
    usage = period_usage(period)
    if any(usage.values()):
        return False, f"El período {period.code} tiene datos registrados: {_describe_usage(usage)}."
    return True, None


def _reassign_active_from(period: AccountingPeriod, *, exclude_ids: set[int], user: User | None) -> None:
    """Move the active flag from ``period`` to the nearest OPEN, visible period not being deleted."""
    candidates = list(
        AccountingPeriod.objects.filter(status=PeriodStatus.OPEN, is_hidden=False).exclude(pk__in=exclude_ids)
    )
    period.is_active = False
    period.save(update_fields=["is_active"])
    if not candidates:
        return
    target_index = period.year * 12 + period.month
    nearest = min(candidates, key=lambda p: (abs(p.year * 12 + p.month - target_index), -(p.year * 12 + p.month)))
    activate_period(nearest, user=user)


def _hard_delete(instance, *, table_name: str, user: User | None, reason: str = "") -> None:
    before = serialize_instance(instance)
    record_id = instance.pk
    try:
        instance.delete()
    except ProtectedError as exc:
        raise ValidationError(
            "No se puede eliminar: existen registros relacionados que lo referencian."
        ) from exc
    after = {"delete_reason": reason} if reason else None
    log_audit(
        action="DELETE",
        table_name=table_name,
        record_id=record_id,
        before_data=before,
        after_data=after,
        user=user,
    )


@transaction.atomic
def delete_period(period: AccountingPeriod, *, user: User, reason: str = "") -> dict:
    """Delete an OPEN accounting period without registered data (ADMIN only).

    If it was the active period, the active flag moves to the nearest open period.
    If its fiscal year ends up without periods, the fiscal year is deleted as well.
    """
    _require_admin(user, "eliminar períodos contables")
    period = AccountingPeriod.objects.select_for_update().select_related("fiscal_year").get(pk=period.pk)
    ok, msg = can_delete_period(period)
    if not ok:
        raise ValidationError(msg)

    fy = period.fiscal_year
    if period.is_active:
        _reassign_active_from(period, exclude_ids={period.pk}, user=user)

    deleted_code = period.code
    _hard_delete(period, table_name="core_accounting_period", user=user, reason=reason)

    fiscal_year_deleted = False
    if not AccountingPeriod.objects.filter(fiscal_year=fy).exists():
        _hard_delete(fy, table_name="core_fiscal_year", user=user, reason=reason)
        fiscal_year_deleted = True

    return {"deleted_period": deleted_code, "fiscal_year_deleted": fiscal_year_deleted}


def fiscal_year_blockers(fy: FiscalYear) -> list[str]:
    """Return human-readable reasons preventing the deletion of ``fy`` (empty list = deletable)."""
    blockers: list[str] = []
    if fy.status != PeriodStatus.OPEN:
        blockers.append(f"El ejercicio {fy.year} está cerrado.")
    for period in fy.periods.all().order_by("month"):
        if period.status != PeriodStatus.OPEN:
            blockers.append(f"{period.month_name} (cerrado)")
            continue
        usage = period_usage(period)
        if any(usage.values()):
            blockers.append(f"{period.month_name} ({_describe_usage(usage)})")
    return blockers


@transaction.atomic
def delete_fiscal_year(fy: FiscalYear, *, user: User, reason: str = "") -> dict:
    """Delete a fiscal year and all its periods, only if none has registered data (ADMIN only)."""
    _require_admin(user, "eliminar ejercicios fiscales")
    fy = FiscalYear.objects.select_for_update().get(pk=fy.pk)
    blockers = fiscal_year_blockers(fy)
    if blockers:
        raise ValidationError(f"No se puede eliminar el ejercicio {fy.year}: {'; '.join(blockers)}.")

    periods = list(AccountingPeriod.objects.select_for_update().filter(fiscal_year=fy))
    period_ids = {p.pk for p in periods}
    active = next((p for p in periods if p.is_active), None)
    if active:
        _reassign_active_from(active, exclude_ids=period_ids, user=user)

    for period in periods:
        _hard_delete(period, table_name="core_accounting_period", user=user, reason=reason)
    year = fy.year
    _hard_delete(fy, table_name="core_fiscal_year", user=user, reason=reason)
    return {"deleted_year": year, "deleted_periods": len(periods)}


# ---------------------------------------------------------------------------
# Visibility (hide / show periods in the selector)
# ---------------------------------------------------------------------------


@transaction.atomic
def set_period_hidden(period: AccountingPeriod, hidden: bool, *, user: User | None = None) -> AccountingPeriod:
    """Hide or show ``period`` in the period selector. The active period cannot be hidden."""
    if hidden and period.is_active:
        raise ValidationError(
            f"El período {period.code} es el período activo; active otro período antes de ocultarlo."
        )
    if period.is_hidden == hidden:
        return period
    before = serialize_instance(period)
    period.is_hidden = hidden
    period.save(update_fields=["is_hidden"])
    log_audit(
        action="UPDATE",
        table_name="core_accounting_period",
        record_id=period.pk,
        before_data=before,
        after_data=serialize_instance(period),
        user=user,
    )
    return period


@transaction.atomic
def set_fiscal_year_hidden(fy: FiscalYear, hidden: bool, *, user: User | None = None) -> int:
    """Hide or show every period of ``fy`` (the active period is always kept visible).

    Returns the number of periods updated.
    """
    updated = 0
    qs = AccountingPeriod.objects.filter(fiscal_year=fy, is_hidden=not hidden)
    if hidden:
        qs = qs.exclude(is_active=True)
    for period in qs:
        set_period_hidden(period, hidden, user=user)
        updated += 1
    return updated


@transaction.atomic
def reopen_period(period: AccountingPeriod, *, user: User, reason: str) -> AccountingPeriod:
    """Reopen the most recently closed accounting period (RF-CIE-05, ADMIN only)."""
    if not user or user.role != User.Role.ADMIN:
        raise ValidationError("Solo un usuario con rol ADMIN puede reabrir un período cerrado.")

    clean_reason = (reason or "").strip()
    if len(clean_reason) < 5:
        raise ValidationError("Debe especificar un motivo válido para reabrir el período.")

    if period.status != PeriodStatus.CLOSED:
        raise ValidationError(f"El período {period.code} ya se encuentra abierto.")

    last_closed = (
        AccountingPeriod.objects.filter(status=PeriodStatus.CLOSED)
        .order_by("-year", "-month")
        .first()
    )
    if last_closed and last_closed.pk != period.pk:
        raise ValidationError(
            f"Solo se puede reabrir el último período cerrado ({last_closed.code})."
        )

    before = serialize_instance(period)
    period.status = PeriodStatus.OPEN
    period.closed_at = None
    period.closed_by = None
    period.save(update_fields=["status", "closed_at", "closed_by"])

    if period.fiscal_year.status == PeriodStatus.CLOSED:
        period.fiscal_year.status = PeriodStatus.OPEN
        period.fiscal_year.save(update_fields=["status"])

    after = serialize_instance(period)
    if after is not None:
        after["reopen_reason"] = clean_reason

    log_audit(
        action="REOPEN",
        table_name="core_accounting_period",
        record_id=period.pk,
        before_data=before,
        after_data=after,
        user=user,
    )
    return period
