import calendar
from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.db import transaction

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
    if not period.is_active:
        period.is_active = True
        period.save(update_fields=["is_active"])
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
def generate_fiscal_year_periods(year: int, *, user: User | None = None) -> FiscalYear:
    """Generate a FiscalYear and its 12 monthly AccountingPeriod rows (RF-CIE-01)."""
    if year < 2000 or year > 2100:
        raise ValidationError("El año fiscal debe estar entre 2000 y 2100.")

    fy, created = FiscalYear.objects.get_or_create(
        year=year,
        defaults={
            "start_date": date(year, 1, 1),
            "end_date": date(year, 12, 31),
            "status": PeriodStatus.OPEN,
        },
    )

    has_any_active = AccountingPeriod.objects.filter(is_active=True).exists()
    for month in range(1, 13):
        last_day = calendar.monthrange(year, month)[1]
        is_default_active = (not has_any_active) and (month == 1)
        period, p_created = AccountingPeriod.objects.get_or_create(
            year=year,
            month=month,
            defaults={
                "fiscal_year": fy,
                "start_date": date(year, month, 1),
                "end_date": date(year, month, last_day),
                "status": PeriodStatus.OPEN,
                "is_active": is_default_active,
            },
        )
        if is_default_active and p_created:
            has_any_active = True

    if created:
        log_audit(
            action="CREATE",
            table_name="core_fiscal_year",
            record_id=fy.pk,
            after_data=serialize_instance(fy),
            user=user,
        )
    return fy


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
