from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry, PeriodBalance
from apps.accounting.serializers import JournalEntrySerializer
from apps.accounting.services.posting import LineDTO, get_account, post_entry
from apps.core.models import AccountingPeriod, AuditLog, PeriodStatus, User
from apps.core.serializers import AccountingPeriodSerializer
from apps.core.services.audit import log_audit, serialize_instance
from apps.reports.services.ledger import get_trial_balance


def _existing_tables() -> set[str]:
    return set(connection.introspection.table_names())


def get_close_preview(period: AccountingPeriod) -> dict:
    """Evaluate pre-close checklist (RF-CIE-02) and compute monthly IVA liquidation preview (RF-CIE-03)."""
    tb = get_trial_balance(period=period)
    row_by_code = {r["code"]: r for r in tb["rows"]}

    # 1. Check no draft entries exist in period
    draft_count = JournalEntry.objects.filter(
        period=period,
        status=JournalEntry.EntryStatus.DRAFT,
    ).count()
    no_drafts_ok = draft_count == 0

    # 2. Check trial balance is balanced
    tb_balanced_ok = bool(tb["totals"]["is_balanced"])

    # 3. Check no unposted sales or purchases in period
    tables = _existing_tables()
    unposted_ops = 0
    with connection.cursor() as cursor:
        if "sales_sale" in tables:
            cursor.execute(
                """
                SELECT COUNT(*) FROM sales_sale
                WHERE period_id = %s AND status = 'ISSUED' AND journal_entry_id IS NULL
                """,
                [period.pk],
            )
            unposted_ops += int(cursor.fetchone()[0] or 0)
        if "purchases_purchase" in tables:
            cursor.execute(
                """
                SELECT COUNT(*) FROM purchases_purchase
                WHERE period_id = %s AND status = 'REGISTERED' AND journal_entry_id IS NULL
                """,
                [period.pk],
            )
            unposted_ops += int(cursor.fetchone()[0] or 0)
    all_ops_posted_ok = unposted_ops == 0

    # 4. Check inventory valuation matches 110401 and 110402 (RN-13)
    acc_inv_vit = get_account("INVENTORY_VITRINA")
    acc_inv_cab = get_account("INVENTORY_CABINA")
    ledger_vitrina = Decimal(row_by_code.get(acc_inv_vit.code, {}).get("closing_balance", "0.00"))
    ledger_cabina = Decimal(row_by_code.get(acc_inv_cab.code, {}).get("closing_balance", "0.00"))
    kardex_vitrina = ledger_vitrina
    kardex_cabina = ledger_cabina
    inventory_reconciled_ok = True

    if "inventory_product" in tables and "inventory_stock" in tables:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM inventory_product WHERE is_active = true")
            product_count = int(cursor.fetchone()[0] or 0)
            if product_count > 0:
                cursor.execute(
                    """
                    SELECT p.inventory_type, COALESCE(SUM(s.quantity * p.average_cost), 0)
                    FROM inventory_product p
                    LEFT JOIN inventory_stock s ON s.product_id = p.id
                    WHERE p.is_active = true
                    GROUP BY p.inventory_type
                    """
                )
                kv = Decimal("0.00")
                kc = Decimal("0.00")
                for inv_type, val in cursor.fetchall():
                    if inv_type == "VITRINA":
                        kv = Decimal(str(val or 0)).quantize(Decimal("0.01"))
                    elif inv_type == "CABINA":
                        kc = Decimal(str(val or 0)).quantize(Decimal("0.01"))
                kardex_vitrina = kv
                kardex_cabina = kc
                inventory_reconciled_ok = (kv == ledger_vitrina) and (kc == ledger_cabina)

    checks = [
        {
            "key": "no_draft_entries",
            "label": "Sin partidas en borrador pendientes",
            "ok": no_drafts_ok,
            "detail": (
                "0 borradores en el período"
                if no_drafts_ok
                else f"Existen {draft_count} partida(s) en estado DRAFT que deben mayorizarse o eliminarse."
            ),
        },
        {
            "key": "trial_balance_balanced",
            "label": "Balance de comprobación cuadrado (Σ Debe = Σ Haber)",
            "ok": tb_balanced_ok,
            "detail": f"Debe ${tb['totals']['debit_total']} = Haber ${tb['totals']['credit_total']}",
        },
        {
            "key": "all_operations_posted",
            "label": "Todas las ventas y compras están contabilizadas",
            "ok": all_ops_posted_ok,
            "detail": (
                "100% de documentos con partida asociada"
                if all_ops_posted_ok
                else f"{unposted_ops} documento(s) sin partida contable."
            ),
        },
        {
            "key": "inventory_matches_ledger",
            "label": f"Conciliación Inventario Kárdex vs Mayor ({acc_inv_vit.code} / {acc_inv_cab.code})",
            "ok": inventory_reconciled_ok,
            "detail": (
                f"Vitrina ${ledger_vitrina:.2f} · Cabina ${ledger_cabina:.2f}"
                if inventory_reconciled_ok
                else f"Diferencia detectada: Mayor (${ledger_vitrina:.2f}/${ledger_cabina:.2f}) vs Kárdex (${kardex_vitrina:.2f}/${kardex_cabina:.2f})"
            ),
        },
    ]

    # 5. Monthly IVA Liquidation calculation (RF-CIE-03)
    acc_iva_debit = get_account("IVA_DEBIT")
    acc_iva_credit = get_account("IVA_CREDIT")
    acc_iva_payable = get_account("IVA_PAYABLE")

    iva_debit = max(
        Decimal("0.00"),
        Decimal(row_by_code.get(acc_iva_debit.code, {}).get("closing_balance", "0.00")),
    )
    iva_credit = max(
        Decimal("0.00"),
        Decimal(row_by_code.get(acc_iva_credit.code, {}).get("closing_balance", "0.00")),
    )

    already_liquidated = JournalEntry.objects.filter(
        period=period,
        entry_type=JournalEntry.EntryType.CLOSING,
        status=JournalEntry.EntryStatus.POSTED,
    ).exists()

    proposed_lines = []
    if iva_debit >= iva_credit:
        iva_payable = iva_debit - iva_credit
        credit_remainder = Decimal("0.00")
        if iva_debit > Decimal("0.00"):
            proposed_lines.append(
                {
                    "account_code": acc_iva_debit.code,
                    "account_name": acc_iva_debit.name,
                    "debit": f"{iva_debit:.2f}",
                    "credit": "0.00",
                }
            )
            if iva_credit > Decimal("0.00"):
                proposed_lines.append(
                    {
                        "account_code": acc_iva_credit.code,
                        "account_name": acc_iva_credit.name,
                        "debit": "0.00",
                        "credit": f"{iva_credit:.2f}",
                    }
                )
            if iva_payable > Decimal("0.00"):
                proposed_lines.append(
                    {
                        "account_code": acc_iva_payable.code,
                        "account_name": acc_iva_payable.name,
                        "debit": "0.00",
                        "credit": f"{iva_payable:.2f}",
                    }
                )
    else:
        # Credit exceeds debit: liquidate all of 2107 IVA débito against 110601 IVA crédito;
        # the remaining credit stays in 110601 as remanente a favor for next month.
        iva_payable = Decimal("0.00")
        credit_remainder = iva_credit - iva_debit
        if iva_debit > Decimal("0.00"):
            proposed_lines.append(
                {
                    "account_code": acc_iva_debit.code,
                    "account_name": acc_iva_debit.name,
                    "debit": f"{iva_debit:.2f}",
                    "credit": "0.00",
                }
            )
            proposed_lines.append(
                {
                    "account_code": acc_iva_credit.code,
                    "account_name": acc_iva_credit.name,
                    "debit": "0.00",
                    "credit": f"{iva_debit:.2f}",
                }
            )

    can_close = period.status == PeriodStatus.OPEN and all(c["ok"] for c in checks)

    return {
        "period": AccountingPeriodSerializer(period).data,
        "can_close": can_close,
        "checks": checks,
        "iva_liquidation": {
            "already_liquidated": already_liquidated,
            "requires_entry": len(proposed_lines) >= 2 and not already_liquidated,
            "iva_debit": f"{iva_debit:.2f}",
            "iva_credit": f"{iva_credit:.2f}",
            "iva_payable": f"{iva_payable:.2f}",
            "credit_remainder": f"{credit_remainder:.2f}",
            "proposed_lines": proposed_lines,
        },
    }


@transaction.atomic
def close_period(
    period: AccountingPeriod,
    *,
    user: User,
    post_iva_liquidation: bool = True,
) -> dict:
    """Execute monthly closing: post IVA liquidation, snapshot PeriodBalance, and lock period (RF-CIE-03, RF-CIE-04)."""
    locked_period = AccountingPeriod.objects.select_for_update().get(pk=period.pk)
    if locked_period.status != PeriodStatus.OPEN:
        raise ValidationError(f"El período {locked_period.code} ya se encuentra cerrado.")

    preview = get_close_preview(locked_period)
    if not preview["can_close"]:
        failed = [c["label"] for c in preview["checks"] if not c["ok"]]
        raise ValidationError(
            f"No se puede cerrar el período {locked_period.code}. Pendiente: {', '.join(failed)}."
        )

    iva_info = preview["iva_liquidation"]
    liquidation_entry = None
    if post_iva_liquidation and iva_info["requires_entry"]:
        lines_dto = [
            LineDTO(
                account=l["account_code"],
                debit=Decimal(l["debit"]),
                credit=Decimal(l["credit"]),
                description=f"Liquidación mensual de IVA — {locked_period.label}",
            )
            for l in iva_info["proposed_lines"]
        ]
        liquidation_entry = post_entry(
            entry_date=locked_period.end_date,
            description=f"Partida de cierre y liquidación mensual de IVA ({locked_period.label})",
            entry_type=JournalEntry.EntryType.CLOSING,
            lines=lines_dto,
            source_app="reports.closing",
            source_id=locked_period.pk,
            user=user,
        )

    # Snapshot balances after IVA liquidation into accounting_period_balance (RF-CIE-04)
    final_tb = get_trial_balance(period=locked_period)
    tb_by_id = {r["account_id"]: r for r in final_tb["rows"]}
    leaf_accounts = Account.objects.filter(accepts_entries=True, is_active=True)

    snapshots_count = 0
    for acc in leaf_accounts:
        row = tb_by_id.get(acc.id)
        open_b = Decimal(row["opening_balance"]) if row else Decimal("0.00")
        deb_t = Decimal(row["debit_total"]) if row else Decimal("0.00")
        cred_t = Decimal(row["credit_total"]) if row else Decimal("0.00")
        close_b = Decimal(row["closing_balance"]) if row else Decimal("0.00")

        PeriodBalance.objects.update_or_create(
            account=acc,
            period=locked_period,
            defaults={
                "opening_balance": open_b,
                "debit_total": deb_t,
                "credit_total": cred_t,
                "closing_balance": close_b,
            },
        )
        snapshots_count += 1

    before = serialize_instance(locked_period)
    was_active = locked_period.is_active
    locked_period.status = PeriodStatus.CLOSED
    locked_period.closed_at = timezone.now()
    locked_period.closed_by = user
    locked_period.save(update_fields=["status", "closed_at", "closed_by"])

    # If the closed period was the active UI period, advance to the next open period if available
    if was_active:
        next_open = (
            AccountingPeriod.objects.filter(
                status=PeriodStatus.OPEN,
                start_date__gt=locked_period.start_date,
            )
            .order_by("year", "month")
            .first()
        )
        if next_open:
            locked_period.is_active = False
            locked_period.save(update_fields=["is_active"])
            next_open.is_active = True
            next_open.save(update_fields=["is_active"])

    log_audit(
        action=AuditLog.Action.CLOSE,
        table_name="core_accounting_period",
        record_id=locked_period.pk,
        before_data=before,
        after_data={
            **serialize_instance(locked_period),
            "snapshots_count": snapshots_count,
            "liquidation_entry_id": liquidation_entry.pk if liquidation_entry else None,
        },
        user=user,
    )

    return {
        "period": AccountingPeriodSerializer(locked_period).data,
        "snapshots_count": snapshots_count,
        "liquidation_entry": (
            JournalEntrySerializer(liquidation_entry).data if liquidation_entry else None
        ),
    }
