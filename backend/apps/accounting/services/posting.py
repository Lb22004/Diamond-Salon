from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db import models, transaction
from django.utils import timezone

from apps.accounting.exceptions import (
    AccountingError,
    ImmutableEntryError,
    InvalidAccountError,
    UnbalancedEntryError,
)
from apps.accounting.models import Account, AccountMapping, JournalEntry, JournalEntryLine
from apps.core.models import AuditLog, PeriodStatus, User
from apps.core.services.audit import log_audit, serialize_instance
from apps.core.services.periods import ClosedPeriodError, get_open_period

TWOPLACES = Decimal("0.01")


def _to_decimal(val: Any) -> Decimal:
    if val is None or val == "":
        return Decimal("0.00")
    return Decimal(str(val)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _coerce_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


@dataclass
class LineDTO:
    """Line transfer object accepted by PostingService (DB_DESIGN.md §6).

    ``account`` can be:
      - an ``Account`` model instance,
      - an integer ``Account.id``,
      - an ``AccountMapping.key`` string (e.g. ``'CASH'``, ``'IVA_DEBIT'``), or
      - a numeric ``Account.code`` string (e.g. ``'110101'``).
    """

    account: Account | int | str
    debit: Decimal | str | int | float = Decimal("0.00")
    credit: Decimal | str | int | float = Decimal("0.00")
    description: str = ""


def get_account(key_or_identifier: Account | int | str) -> Account:
    """Resolve an Account from ``AccountMapping`` key, account ID, or account code (RN-12)."""
    if isinstance(key_or_identifier, Account):
        return key_or_identifier

    if isinstance(key_or_identifier, int):
        acc = Account.objects.filter(pk=key_or_identifier).first()
        if not acc:
            raise InvalidAccountError(f"No existe la cuenta contable con ID #{key_or_identifier}.")
        return acc

    key_str = str(key_or_identifier).strip()
    mapping = AccountMapping.objects.select_related("account").filter(key=key_str).first()
    if mapping:
        return mapping.account

    if key_str.isdigit():
        acc = Account.objects.filter(code=key_str).first() or Account.objects.filter(pk=int(key_str)).first()
        if acc:
            return acc

    raise InvalidAccountError(
        f"No se encontró configuración de cuenta contable para «{key_str}»."
    )


def _normalize_lines(raw_lines: list[LineDTO | dict | tuple]) -> list[tuple[Account, Decimal, Decimal, str]]:
    if not raw_lines or len(raw_lines) < 2:
        raise UnbalancedEntryError("Toda partida contable requiere al menos 2 líneas de movimiento.")

    normalized: list[tuple[Account, Decimal, Decimal, str]] = []
    for idx, item in enumerate(raw_lines, start=1):
        if isinstance(item, LineDTO):
            acc_ref = item.account
            debit = _to_decimal(item.debit)
            credit = _to_decimal(item.credit)
            desc = item.description or ""
        elif isinstance(item, dict):
            acc_ref = (
                item.get("account")
                or item.get("account_id")
                or item.get("account_key")
                or item.get("account_code")
            )
            debit = _to_decimal(item.get("debit", "0.00"))
            credit = _to_decimal(item.get("credit", "0.00"))
            desc = item.get("description") or ""
        elif isinstance(item, (tuple, list)):
            acc_ref = item[0]
            debit = _to_decimal(item[1] if len(item) > 1 else "0.00")
            credit = _to_decimal(item[2] if len(item) > 2 else "0.00")
            desc = str(item[3]) if len(item) > 3 and item[3] is not None else ""
        else:
            raise UnbalancedEntryError(f"Formato inválido en la línea #{idx}.")

        if debit < Decimal("0.00") or credit < Decimal("0.00"):
            raise UnbalancedEntryError(f"Línea #{idx}: los montos de Debe y Haber no pueden ser negativos.")

        if (debit > Decimal("0.00") and credit > Decimal("0.00")) or (
            debit == Decimal("0.00") and credit == Decimal("0.00")
        ):
            raise UnbalancedEntryError(
                f"Línea #{idx}: cada movimiento debe tener monto en Debe o en Haber (nunca ambos ni cero)."
            )

        account = get_account(acc_ref)
        if not account.is_active:
            raise InvalidAccountError(
                f"La cuenta {account.code} ({account.name}) se encuentra inactiva."
            )
        if not account.accepts_entries:
            raise InvalidAccountError(
                f"La cuenta {account.code} ({account.name}) es de agrupación y no acepta movimientos directos (RN-04)."
            )

        normalized.append((account, debit, credit, desc.strip()))

    return normalized


def _resolve_user(user: User | None) -> User:
    if user and getattr(user, "is_authenticated", False):
        return user
    fallback = User.objects.filter(username="system").first() or User.objects.first()
    if not fallback:
        raise InvalidAccountError("No existe un usuario válido para registrar la partida.")
    return fallback


@transaction.atomic
def create_draft_entry(
    *,
    entry_date: date | datetime | str,
    description: str,
    entry_type: str = JournalEntry.EntryType.MANUAL,
    lines: list[LineDTO | dict | tuple],
    source_app: str | None = None,
    source_id: int | None = None,
    user: User | None = None,
) -> JournalEntry:
    """Create a DRAFT journal entry and its lines inside an open period (RF-DIA-03)."""
    target_date = _coerce_date(entry_date)
    period = get_open_period(target_date)
    actor = _resolve_user(user)
    normalized_lines = _normalize_lines(lines)

    clean_desc = (description or "").strip()
    if not clean_desc:
        raise UnbalancedEntryError("El concepto o descripción de la partida es obligatorio.")

    entry = JournalEntry.objects.create(
        period=period,
        entry_number=None,
        entry_date=target_date,
        description=clean_desc,
        entry_type=entry_type,
        source_app=source_app,
        source_id=source_id,
        status=JournalEntry.EntryStatus.DRAFT,
        total_debit=Decimal("0.00"),
        total_credit=Decimal("0.00"),
        created_by=actor,
    )

    total_d = Decimal("0.00")
    total_c = Decimal("0.00")
    for line_no, (account, debit, credit, line_desc) in enumerate(normalized_lines, start=1):
        JournalEntryLine.objects.create(
            entry=entry,
            line_no=line_no,
            account=account,
            description=line_desc,
            debit=debit,
            credit=credit,
        )
        total_d += debit
        total_c += credit

    entry.total_debit = total_d
    entry.total_credit = total_c
    entry.save(update_fields=["total_debit", "total_credit"])

    log_audit(
        action=AuditLog.Action.CREATE,
        table_name="accounting_journal_entry",
        record_id=entry.pk,
        after_data=serialize_instance(entry),
        user=actor,
    )
    return entry


@transaction.atomic
def update_draft_entry(
    entry: JournalEntry,
    *,
    entry_date: date | datetime | str | None = None,
    description: str | None = None,
    lines: list[LineDTO | dict | tuple] | None = None,
    user: User | None = None,
) -> JournalEntry:
    """Update a DRAFT entry and replace its lines. Blocked for POSTED/REVERSED entries (RN-02)."""
    if entry.status != JournalEntry.EntryStatus.DRAFT:
        raise ImmutableEntryError(
            f"La partida N.º {entry.entry_number or entry.pk} ya está mayorizada y es inmutable; utilice una reversión."
        )

    before = serialize_instance(entry)
    actor = _resolve_user(user)

    if entry_date is not None:
        target_date = _coerce_date(entry_date)
        period = get_open_period(target_date)
        entry.entry_date = target_date
        entry.period = period

    if description is not None:
        clean_desc = description.strip()
        if not clean_desc:
            raise UnbalancedEntryError("El concepto de la partida es obligatorio.")
        entry.description = clean_desc

    if lines is not None:
        normalized_lines = _normalize_lines(lines)
        entry.lines.all().delete()
        total_d = Decimal("0.00")
        total_c = Decimal("0.00")
        for line_no, (account, debit, credit, line_desc) in enumerate(normalized_lines, start=1):
            JournalEntryLine.objects.create(
                entry=entry,
                line_no=line_no,
                account=account,
                description=line_desc,
                debit=debit,
                credit=credit,
            )
            total_d += debit
            total_c += credit
        entry.total_debit = total_d
        entry.total_credit = total_c

    entry.save()
    log_audit(
        action=AuditLog.Action.UPDATE,
        table_name="accounting_journal_entry",
        record_id=entry.pk,
        before_data=before,
        after_data=serialize_instance(entry),
        user=actor,
    )
    return entry


@transaction.atomic
def delete_draft_entry(entry: JournalEntry, *, user: User | None = None) -> None:
    """Delete a DRAFT journal entry. Posted entries cannot be deleted (RN-02)."""
    if entry.status != JournalEntry.EntryStatus.DRAFT:
        raise ImmutableEntryError(
            f"La partida N.º {entry.entry_number or entry.pk} ya está mayorizada y no puede eliminarse; utilice una reversión."
        )
    before = serialize_instance(entry)
    record_id = entry.pk
    actor = _resolve_user(user)
    entry.delete()
    log_audit(
        action=AuditLog.Action.DELETE,
        table_name="accounting_journal_entry",
        record_id=record_id,
        before_data=before,
        user=actor,
    )


@transaction.atomic
def post_draft_entry(entry: JournalEntry, *, user: User | None = None) -> JournalEntry:
    """Validate and post an existing DRAFT entry, assigning sequential entry_number in the period."""
    locked_entry = (
        JournalEntry.objects.select_for_update()
        .select_related("period", "period__fiscal_year")
        .get(pk=entry.pk)
    )
    if locked_entry.status != JournalEntry.EntryStatus.DRAFT:
        raise ImmutableEntryError(
            f"La partida N.º {locked_entry.entry_number or locked_entry.pk} ya fue mayorizada."
        )

    period = locked_entry.period
    if period.status != PeriodStatus.OPEN or period.fiscal_year.status != PeriodStatus.OPEN:
        raise ClosedPeriodError(f"El período {period.month:02d}/{period.year} está cerrado")

    if not (period.start_date <= locked_entry.entry_date <= period.end_date):
        raise ClosedPeriodError(
            f"La fecha de la partida ({locked_entry.entry_date}) está fuera del período {period.code}."
        )

    lines = list(locked_entry.lines.select_related("account").all())
    if len(lines) < 2:
        raise UnbalancedEntryError("La partida debe contener al menos 2 líneas para mayorizarse (RN-01).")

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")
    for line in lines:
        if not line.account.is_active or not line.account.accepts_entries:
            raise InvalidAccountError(
                f"La cuenta {line.account.code} ({line.account.name}) no acepta movimientos o está inactiva."
            )
        total_debit += line.debit
        total_credit += line.credit

    diff = abs(total_debit - total_credit)
    if diff != Decimal("0.00") or total_debit <= Decimal("0.00"):
        raise UnbalancedEntryError(f"La partida no está cuadrada (diferencia ${diff:.2f})")

    # Sequential entry_number per period with row lock on period entries
    max_num = (
        JournalEntry.objects.select_for_update()
        .filter(period=period, entry_number__isnull=False)
        .aggregate(max_n=models.Max("entry_number"))["max_n"]
        or 0
    )

    before = serialize_instance(locked_entry)
    actor = _resolve_user(user)
    locked_entry.entry_number = max_num + 1
    locked_entry.status = JournalEntry.EntryStatus.POSTED
    locked_entry.total_debit = total_debit
    locked_entry.total_credit = total_credit
    locked_entry.posted_by = actor
    locked_entry.posted_at = timezone.now()
    locked_entry.save()

    log_audit(
        action=AuditLog.Action.POST,
        table_name="accounting_journal_entry",
        record_id=locked_entry.pk,
        before_data=before,
        after_data=serialize_instance(locked_entry),
        user=actor,
    )
    return locked_entry


@transaction.atomic
def post_entry(
    *,
    entry_date: date | datetime | str,
    description: str,
    entry_type: str,
    lines: list[LineDTO | dict | tuple],
    source_app: str | None = None,
    source_id: int | None = None,
    user: User | None = None,
) -> JournalEntry:
    """Validates and creates a POSTED entry atomically (DB_DESIGN.md §6 contract).

    Raises ``UnbalancedEntryError``, ``ClosedPeriodError``, ``InvalidAccountError``.
    Uses the 2-step DRAFT -> POSTED transition required by PostgreSQL's ``trg_journal_entry_guard``.
    """
    draft = create_draft_entry(
        entry_date=entry_date,
        description=description,
        entry_type=entry_type,
        lines=lines,
        source_app=source_app,
        source_id=source_id,
        user=user,
    )
    return post_draft_entry(draft, user=user)


@transaction.atomic
def reverse_entry(
    entry: JournalEntry,
    *,
    reason: str,
    user: User | None = None,
    reversal_date: date | datetime | str | None = None,
) -> JournalEntry:
    """Create and post a mirror-image reversal entry, marking the original REVERSED (RN-02, RF-DIA-04)."""
    clean_reason = (reason or "").strip()
    if len(clean_reason) < 3:
        raise AccountingError("Debe especificar el motivo de la reversión.")

    locked_original = (
        JournalEntry.objects.select_for_update()
        .select_related("period")
        .prefetch_related("lines__account")
        .get(pk=entry.pk)
    )

    if locked_original.status == JournalEntry.EntryStatus.REVERSED:
        raise ImmutableEntryError(
            f"La partida N.º {locked_original.entry_number} ya fue revertida anteriormente."
        )
    if locked_original.status != JournalEntry.EntryStatus.POSTED:
        raise ImmutableEntryError("Solo se pueden revertir partidas con estado MAYORIZADA (POSTED).")

    target_date = _coerce_date(reversal_date) if reversal_date else locked_original.entry_date
    # Verify target period is open before mutating
    get_open_period(target_date)

    actor = _resolve_user(user)
    before_orig = serialize_instance(locked_original)

    # Mirror lines: swap debit and credit
    mirror_lines = [
        LineDTO(
            account=line.account,
            debit=line.credit,
            credit=line.debit,
            description=f"Reversión Part. N.º {locked_original.entry_number}: {line.description or locked_original.description}"[:255],
        )
        for line in locked_original.lines.all()
    ]

    reversal_desc = (
        f"Reversión de Partida N.º {locked_original.entry_number} — Motivo: {clean_reason}"
    )
    draft_reversal = create_draft_entry(
        entry_date=target_date,
        description=reversal_desc,
        entry_type=JournalEntry.EntryType.REVERSAL,
        lines=mirror_lines,
        source_app=locked_original.source_app,
        source_id=locked_original.source_id,
        user=actor,
    )
    draft_reversal.reversal_of = locked_original
    draft_reversal.save(update_fields=["reversal_of"])

    posted_reversal = post_draft_entry(draft_reversal, user=actor)

    # Transition original POSTED -> REVERSED (only field allowed to change by trg_journal_entry_guard)
    locked_original.status = JournalEntry.EntryStatus.REVERSED
    locked_original.save(update_fields=["status"])

    log_audit(
        action=AuditLog.Action.REVERSE,
        table_name="accounting_journal_entry",
        record_id=locked_original.pk,
        before_data=before_orig,
        after_data={
            **serialize_instance(locked_original),
            "reversed_by_id": posted_reversal.pk,
            "reversed_by_number": posted_reversal.entry_number,
            "reason": clean_reason,
        },
        user=actor,
    )
    return posted_reversal
