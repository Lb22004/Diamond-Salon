from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, Q, Sum

from apps.accounting.models import Account, JournalEntry, JournalEntryLine
from apps.accounting.serializers import AccountSerializer
from apps.core.models import AccountingPeriod
from apps.core.serializers import AccountingPeriodSerializer
from apps.core.services.periods import get_active_period

TWOPLACES = Decimal("0.01")

KEY_SIMULTANEOUS_CODES = [
    "110101",  # Caja general
    "110102",  # Bancos
    "110501",  # Mercadería vitrina
    "110502",  # Insumos cabina
    "110601",  # IVA crédito fiscal
    "2107",    # IVA débito fiscal
    "210101",  # Proveedores locales
    "5101",    # Ingresos servicios
    "5102",    # Ingresos productos
]


def _coerce_date(val: date | datetime | str | None, fallback: date) -> date:
    if not val:
        return fallback
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return date.fromisoformat(str(val)[:10])


def _resolve_account(identifier: Account | int | str | None) -> Account:
    if isinstance(identifier, Account):
        return identifier
    if identifier:
        s = str(identifier).strip()
        acc = Account.objects.filter(code=s).first()
        if not acc and s.isdigit():
            acc = Account.objects.filter(pk=int(s)).first()
        if acc:
            return acc
    return (
        Account.objects.filter(code="110101").first()
        or Account.objects.filter(accepts_entries=True, is_active=True).order_by("code").first()
        or Account.objects.order_by("code").first()
    )


def _signed_delta(nature: str, debit: Decimal, credit: Decimal) -> Decimal:
    if nature == Account.Nature.DEBIT:
        return debit - credit
    return credit - debit


def get_simultaneous_summary(cutoff_date: date) -> list[dict]:
    """Return current balances of key related accounts ('Resumen mayorizado simultáneo' · RF-MAY-08)."""
    accounts = list(Account.objects.filter(code__in=KEY_SIMULTANEOUS_CODES).order_by("code"))
    if not accounts:
        return []

    sums = (
        JournalEntryLine.objects.filter(
            account__in=accounts,
            entry__status__in=[JournalEntry.EntryStatus.POSTED, JournalEntry.EntryStatus.REVERSED],
            entry__entry_date__lte=cutoff_date,
        )
        .values("account_id")
        .annotate(
            d_sum=Sum("debit"),
            c_sum=Sum("credit"),
            cnt=Count("id"),
        )
    )
    sum_map = {
        r["account_id"]: (
            r["d_sum"] or Decimal("0.00"),
            r["c_sum"] or Decimal("0.00"),
            int(r["cnt"] or 0),
        )
        for r in sums
    }

    cards = []
    for acc in accounts:
        d_tot, c_tot, cnt = sum_map.get(acc.id, (Decimal("0.00"), Decimal("0.00"), 0))
        bal = _signed_delta(acc.nature, d_tot, c_tot)
        cards.append(
            {
                "id": acc.id,
                "code": acc.code,
                "name": acc.name,
                "classification": acc.classification or acc.level_label,
                "nature": acc.nature,
                "nature_label": acc.get_nature_display(),
                "inventory_type": acc.inventory_type,
                "debit_total": f"{d_tot:.2f}",
                "credit_total": f"{c_tot:.2f}",
                "balance": f"{bal:.2f}",
                "movements_count": cnt,
            }
        )
    return cards


def get_account_ledger(
    *,
    account_identifier: Account | int | str | None = None,
    period: AccountingPeriod | None = None,
    date_from: date | str | None = None,
    date_to: date | str | None = None,
) -> dict:
    """Compute General Ledger (Libro Mayor) for an account and date range (RF-MAY-01..08)."""
    resolved_period = period or get_active_period()
    default_start = resolved_period.start_date if resolved_period else date(2026, 11, 1)
    default_end = resolved_period.end_date if resolved_period else date(2026, 11, 30)

    start_d = _coerce_date(date_from, default_start)
    end_d = _coerce_date(date_to, default_end)
    account = _resolve_account(account_identifier)

    # Support querying either a leaf account or a parent grouping account by code prefix
    if account.accepts_entries:
        acc_filter = Q(account=account)
    else:
        acc_filter = Q(account__code__startswith=account.code)

    posted_statuses = [JournalEntry.EntryStatus.POSTED, JournalEntry.EntryStatus.REVERSED]

    # 1. Opening balance strictly before start_d ( plus any OPENING entry on start_d if no prior movements exist )
    prior_agg = JournalEntryLine.objects.filter(
        acc_filter,
        entry__status__in=posted_statuses,
        entry__entry_date__lt=start_d,
    ).aggregate(
        d_sum=Sum("debit"),
        c_sum=Sum("credit"),
    )
    prior_debit = prior_agg["d_sum"] or Decimal("0.00")
    prior_credit = prior_agg["c_sum"] or Decimal("0.00")
    opening_balance = _signed_delta(account.nature, prior_debit, prior_credit)

    # 2. Chronological movements inside [start_d, end_d]
    lines_qs = (
        JournalEntryLine.objects.filter(
            acc_filter,
            entry__status__in=posted_statuses,
            entry__entry_date__gte=start_d,
            entry__entry_date__lte=end_d,
        )
        .select_related("entry", "account")
        .order_by("entry__entry_date", "entry__entry_number", "entry__id", "line_no")
    )

    running = opening_balance
    debit_total = Decimal("0.00")
    credit_total = Decimal("0.00")
    debit_count = 0
    credit_count = 0
    opening_in_range = Decimal("0.00")
    movements = []

    for line in lines_qs:
        d = line.debit or Decimal("0.00")
        c = line.credit or Decimal("0.00")
        delta = _signed_delta(account.nature, d, c)
        running += delta
        debit_total += d
        credit_total += c
        if d > Decimal("0.00"):
            debit_count += 1
        if c > Decimal("0.00"):
            credit_count += 1
        if line.entry.entry_type == JournalEntry.EntryType.OPENING:
            opening_in_range += delta

        movements.append(
            {
                "line_id": line.id,
                "entry_id": line.entry_id,
                "entry_number": line.entry.entry_number,
                "entry_ref": f"Part. N.º {line.entry.entry_number}" if line.entry.entry_number else f"#{line.entry_id}",
                "entry_date": line.entry.entry_date.isoformat(),
                "entry_type": line.entry.entry_type,
                "entry_type_label": line.entry.get_entry_type_display(),
                "entry_status": line.entry.status,
                "source_app": line.entry.source_app,
                "source_id": line.entry.source_id,
                "account_code": line.account.code,
                "account_name": line.account.name,
                "concept": line.description or line.entry.description,
                "debit": f"{d:.2f}",
                "credit": f"{c:.2f}",
                "resulting_balance": f"{running:.2f}",
            }
        )

    closing_balance = running
    # Effective initial reference for KPI card & variation % (OI-8):
    # If opening_balance before the first period is 0 but an OPENING entry exists inside the period,
    # expose both opening_balance (strictly prior to start_d) and effective_initial_balance.
    effective_initial = opening_balance if opening_balance != Decimal("0.00") else opening_in_range
    operational_inflow = (
        debit_total - opening_in_range
        if account.nature == Account.Nature.DEBIT and opening_balance == Decimal("0.00")
        else debit_total
    )
    if effective_initial > Decimal("0.00"):
        net_change = closing_balance - effective_initial
        variation_pct = ((net_change / effective_initial) * Decimal("100")).quantize(
            TWOPLACES, rounding=ROUND_HALF_UP
        )
    else:
        variation_pct = Decimal("0.00")

    # 3. Verify period trial balance equality (RF-MAY-06: "Sumas iguales verificadas: OK")
    tb_agg = JournalEntryLine.objects.filter(
        entry__status__in=posted_statuses,
        entry__entry_date__gte=start_d,
        entry__entry_date__lte=end_d,
    ).aggregate(td=Sum("debit"), tc=Sum("credit"))
    tb_debit = tb_agg["td"] or Decimal("0.00")
    tb_credit = tb_agg["tc"] or Decimal("0.00")

    return {
        "account": AccountSerializer(account).data,
        "period": AccountingPeriodSerializer(resolved_period).data if resolved_period else None,
        "date_from": start_d.isoformat(),
        "date_to": end_d.isoformat(),
        "kpis": {
            "opening_balance": f"{opening_balance:.2f}",
            "effective_initial_balance": f"{effective_initial:.2f}",
            "debit_total": f"{debit_total:.2f}",
            "debit_count": debit_count,
            "credit_total": f"{credit_total:.2f}",
            "credit_count": credit_count,
            "closing_balance": f"{closing_balance:.2f}",
            "variation_pct": f"{variation_pct:+.2f}%",
            "operational_inflow": f"{operational_inflow:.2f}",
        },
        "verification": {
            "trial_balance_ok": tb_debit == tb_credit,
            "period_total_debit": f"{tb_debit:.2f}",
            "period_total_credit": f"{tb_credit:.2f}",
        },
        "movements": movements,
        "simultaneous_summary": get_simultaneous_summary(end_d),
    }


def get_trial_balance(*, period: AccountingPeriod | None = None) -> dict:
    """Compute Trial Balance (Balance de Comprobación de Sumas y Saldos · RF-MAY-10)."""
    resolved_period = period or get_active_period()
    start_d = resolved_period.start_date if resolved_period else date(2026, 11, 1)
    end_d = resolved_period.end_date if resolved_period else date(2026, 11, 30)

    posted_statuses = [JournalEntry.EntryStatus.POSTED, JournalEntry.EntryStatus.REVERSED]
    leaf_accounts = list(
        Account.objects.filter(accepts_entries=True, is_active=True).order_by("code")
    )

    prior_sums = {
        r["account_id"]: (r["d"] or Decimal("0.00"), r["c"] or Decimal("0.00"))
        for r in JournalEntryLine.objects.filter(
            entry__status__in=posted_statuses,
            entry__entry_date__lt=start_d,
        )
        .values("account_id")
        .annotate(d=Sum("debit"), c=Sum("credit"))
    }

    period_sums = {
        r["account_id"]: (r["d"] or Decimal("0.00"), r["c"] or Decimal("0.00"))
        for r in JournalEntryLine.objects.filter(
            entry__status__in=posted_statuses,
            entry__entry_date__gte=start_d,
            entry__entry_date__lte=end_d,
        )
        .values("account_id")
        .annotate(d=Sum("debit"), c=Sum("credit"))
    }

    rows = []
    sum_opening_debit = Decimal("0.00")
    sum_opening_credit = Decimal("0.00")
    sum_debit = Decimal("0.00")
    sum_credit = Decimal("0.00")
    sum_closing_debit = Decimal("0.00")
    sum_closing_credit = Decimal("0.00")

    for acc in leaf_accounts:
        pd, pc = prior_sums.get(acc.id, (Decimal("0.00"), Decimal("0.00")))
        md, mc = period_sums.get(acc.id, (Decimal("0.00"), Decimal("0.00")))
        if pd == Decimal("0.00") and pc == Decimal("0.00") and md == Decimal("0.00") and mc == Decimal("0.00"):
            continue

        opening_signed = _signed_delta(acc.nature, pd, pc)
        closing_signed = _signed_delta(acc.nature, pd + md, pc + mc)

        if acc.nature == Account.Nature.DEBIT:
            open_d = max(Decimal("0.00"), opening_signed)
            open_c = max(Decimal("0.00"), -opening_signed)
            close_d = max(Decimal("0.00"), closing_signed)
            close_c = max(Decimal("0.00"), -closing_signed)
        else:
            open_c = max(Decimal("0.00"), opening_signed)
            open_d = max(Decimal("0.00"), -opening_signed)
            close_c = max(Decimal("0.00"), closing_signed)
            close_d = max(Decimal("0.00"), -closing_signed)

        sum_opening_debit += open_d
        sum_opening_credit += open_c
        sum_debit += md
        sum_credit += mc
        sum_closing_debit += close_d
        sum_closing_credit += close_c

        rows.append(
            {
                "account_id": acc.id,
                "code": acc.code,
                "name": acc.name,
                "account_type": acc.account_type,
                "account_type_label": acc.get_account_type_display(),
                "nature": acc.nature,
                "nature_label": acc.get_nature_display(),
                "inventory_type": acc.inventory_type,
                "opening_balance": f"{opening_signed:.2f}",
                "opening_debit": f"{open_d:.2f}",
                "opening_credit": f"{open_c:.2f}",
                "debit_total": f"{md:.2f}",
                "credit_total": f"{mc:.2f}",
                "closing_balance": f"{closing_signed:.2f}",
                "closing_debit": f"{close_d:.2f}",
                "closing_credit": f"{close_c:.2f}",
            }
        )

    is_balanced = (sum_debit == sum_credit) and (sum_closing_debit == sum_closing_credit)
    return {
        "period": AccountingPeriodSerializer(resolved_period).data if resolved_period else None,
        "rows": rows,
        "totals": {
            "opening_debit": f"{sum_opening_debit:.2f}",
            "opening_credit": f"{sum_opening_credit:.2f}",
            "debit_total": f"{sum_debit:.2f}",
            "credit_total": f"{sum_credit:.2f}",
            "closing_debit": f"{sum_closing_debit:.2f}",
            "closing_credit": f"{sum_closing_credit:.2f}",
            "is_balanced": is_balanced,
        },
    }


def get_financial_statements(*, period: AccountingPeriod | None = None) -> dict:
    """Compute Estado de Resultados (RF-REP-02) and Balance General (RF-REP-03) under NIIF PYMES."""
    tb = get_trial_balance(period=period)
    rows = tb["rows"]

    incomes = []
    costs = []
    expenses = []
    assets = []
    liabilities = []
    equity = []

    total_income = Decimal("0.00")
    total_cost = Decimal("0.00")
    total_expense = Decimal("0.00")
    total_assets = Decimal("0.00")
    total_liabilities = Decimal("0.00")
    total_equity = Decimal("0.00")

    for r in rows:
        bal = Decimal(r["closing_balance"])
        acc_type = r["account_type"]
        item = {
            "code": r["code"],
            "name": r["name"],
            "inventory_type": r["inventory_type"],
            "balance": f"{bal:.2f}",
        }
        if acc_type == Account.AccountType.INCOME:
            incomes.append(item)
            total_income += bal
        elif acc_type == Account.AccountType.COST:
            costs.append(item)
            total_cost += bal
        elif acc_type == Account.AccountType.EXPENSE:
            expenses.append(item)
            total_expense += bal
        elif acc_type == Account.AccountType.ASSET:
            assets.append(item)
            total_assets += bal
        elif acc_type == Account.AccountType.LIABILITY:
            liabilities.append(item)
            total_liabilities += bal
        elif acc_type == Account.AccountType.EQUITY:
            equity.append(item)
            total_equity += bal

    gross_profit = total_income - total_cost
    net_income = gross_profit - total_expense
    total_equity_with_result = total_equity + net_income
    liabilities_plus_equity = total_liabilities + total_equity_with_result

    return {
        "period": tb["period"],
        "income_statement": {
            "incomes": incomes,
            "costs": costs,
            "expenses": expenses,
            "total_income": f"{total_income:.2f}",
            "total_cost": f"{total_cost:.2f}",
            "gross_profit": f"{gross_profit:.2f}",
            "total_expense": f"{total_expense:.2f}",
            "net_income": f"{net_income:.2f}",
        },
        "balance_sheet": {
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "total_assets": f"{total_assets:.2f}",
            "total_liabilities": f"{total_liabilities:.2f}",
            "total_equity_base": f"{total_equity:.2f}",
            "current_period_result": f"{net_income:.2f}",
            "total_equity": f"{total_equity_with_result:.2f}",
            "total_liabilities_and_equity": f"{liabilities_plus_equity:.2f}",
            "is_balanced": total_assets == liabilities_plus_equity,
        },
    }
