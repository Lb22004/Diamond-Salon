from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounting.models import Account, AccountMapping, JournalEntry, JournalEntryLine
from apps.accounting.serializers import (
    AccountMappingSerializer,
    AccountSerializer,
    JournalEntrySerializer,
    JournalEntryWriteSerializer,
)
from apps.accounting.services.posting import (
    create_draft_entry,
    delete_draft_entry,
    post_draft_entry,
    post_entry,
    reverse_entry,
    update_draft_entry,
)
from apps.core.exceptions import ClosedPeriodError
from apps.core.models import AccountingPeriod, AuditLog
from apps.core.permissions import IsAccountantOrAdmin
from apps.core.services.audit import log_audit, serialize_instance
from apps.core.services.periods import get_active_period


def _compute_account_balances(period: AccountingPeriod | None = None):
    """Compute debit, credit, signed balance, and movement counts for every account (DB_DESIGN.md §5)."""
    line_qs = JournalEntryLine.objects.filter(
        entry__status__in=[JournalEntry.EntryStatus.POSTED, JournalEntry.EntryStatus.REVERSED]
    )
    if period is not None:
        line_qs = line_qs.filter(entry__entry_date__lte=period.end_date)

    leaf_sums = line_qs.values("account__code").annotate(
        d_sum=Sum("debit"),
        c_sum=Sum("credit"),
        cnt=Count("id"),
    )

    all_move_codes = set(
        JournalEntryLine.objects.values_list("account__code", flat=True).distinct()
    )

    leaf_map: dict[str, tuple[Decimal, Decimal, int]] = {}
    for row in leaf_sums:
        code = row["account__code"]
        leaf_map[code] = (
            row["d_sum"] or Decimal("0.00"),
            row["c_sum"] or Decimal("0.00"),
            int(row["cnt"] or 0),
        )

    return leaf_map, all_move_codes


def _enrich_accounts(accounts: list[Account], period: AccountingPeriod | None = None) -> tuple[list[dict], dict]:
    leaf_map, all_move_codes = _compute_account_balances(period)

    total_leaf_debit = sum((v[0] for v in leaf_map.values()), Decimal("0.00"))
    total_leaf_credit = sum((v[1] for v in leaf_map.values()), Decimal("0.00"))

    class_counts = {
        "ALL": len(accounts),
        "ASSET": 0,
        "LIABILITY": 0,
        "EQUITY": 0,
        "COST_EXPENSE": 0,
        "INCOME": 0,
    }

    serialized_list: list[dict] = []
    for acc in accounts:
        if acc.account_type == Account.AccountType.ASSET:
            class_counts["ASSET"] += 1
        elif acc.account_type == Account.AccountType.LIABILITY:
            class_counts["LIABILITY"] += 1
        elif acc.account_type == Account.AccountType.EQUITY:
            class_counts["EQUITY"] += 1
        elif acc.account_type in (Account.AccountType.COST, Account.AccountType.EXPENSE):
            class_counts["COST_EXPENSE"] += 1
        elif acc.account_type == Account.AccountType.INCOME:
            class_counts["INCOME"] += 1

        # Roll up descendants by code prefix (DB_DESIGN.md §5)
        d_tot = Decimal("0.00")
        c_tot = Decimal("0.00")
        for leaf_code, (ld, lc, _) in leaf_map.items():
            if leaf_code == acc.code or leaf_code.startswith(acc.code):
                d_tot += ld
                c_tot += lc

        if acc.nature == Account.Nature.DEBIT:
            bal = d_tot - c_tot
        else:
            bal = c_tot - d_tot

        has_moves = any(
            mc == acc.code or mc.startswith(acc.code) for mc in all_move_codes
        )

        acc.has_movements = has_moves
        acc.debit_total = f"{d_tot:.2f}"
        acc.credit_total = f"{c_tot:.2f}"
        acc.balance = f"{bal:.2f}"

        serialized_list.append(AccountSerializer(acc).data)

    summary = {
        "total_debit": f"{total_leaf_debit:.2f}",
        "total_credit": f"{total_leaf_credit:.2f}",
        "is_balanced": total_leaf_debit == total_leaf_credit,
        "class_counts": class_counts,
    }
    return serialized_list, summary


def _build_tree(flat_items: list[dict]) -> list[dict]:
    by_id: dict[int, dict] = {}
    roots: list[dict] = []
    for item in flat_items:
        node = {**item, "children": []}
        by_id[node["id"]] = node

    for item in flat_items:
        node = by_id[item["id"]]
        parent_id = node.get("parent")
        if parent_id and parent_id in by_id:
            by_id[parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


class AccountViewSet(viewsets.ModelViewSet):
    """Chart of Accounts CRUD & hierarchical query endpoint (Vista 1 · RF-CAT-01..12)."""

    queryset = Account.objects.select_related("parent").order_by("code")
    serializer_class = AccountSerializer
    permission_classes = [IsAccountantOrAdmin]
    pagination_class = None  # Chart of accounts is returned complete for hierarchical tree rendering

    def list(self, request, *args, **kwargs):
        period_id = request.query_params.get("period")
        period = (
            AccountingPeriod.objects.filter(pk=period_id).first()
            if period_id
            else get_active_period()
        )

        qs = self.get_queryset()
        include_inactive = request.query_params.get("include_inactive") in ("1", "true")
        if not include_inactive:
            qs = qs.filter(is_active=True)

        accounts = list(qs)
        flat_items, summary = _enrich_accounts(accounts, period)

        # Optional filters applied after computing full class_counts & parent rollups
        account_type = request.query_params.get("account_type")
        if account_type == "COST_EXPENSE":
            flat_items = [a for a in flat_items if a["account_type"] in ("COST", "EXPENSE")]
        elif account_type:
            flat_items = [a for a in flat_items if a["account_type"] == account_type]

        accepts_entries = request.query_params.get("accepts_entries")
        if accepts_entries in ("1", "true"):
            flat_items = [a for a in flat_items if a["accepts_entries"]]

        search = (request.query_params.get("search") or "").strip().lower()
        if search:
            flat_items = [
                a
                for a in flat_items
                if search in a["code"].lower()
                or search in a["name"].lower()
                or search in (a["classification"] or "").lower()
            ]

        if request.query_params.get("tree") in ("1", "true"):
            return Response(
                {
                    "summary": summary,
                    "results": flat_items,
                    "tree": _build_tree(flat_items),
                }
            )

        return Response(flat_items)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        period = get_active_period()
        enriched, _ = _enrich_accounts([instance], period)
        return Response(enriched[0])

    def perform_create(self, serializer):
        instance: Account = serializer.save()
        # If parent was marked accepts_entries=True (with 0 movements), convert parent to grouping
        if instance.parent and instance.parent.accepts_entries:
            instance.parent.accepts_entries = False
            instance.parent.save(update_fields=["accepts_entries"])

        log_audit(
            action=AuditLog.Action.CREATE,
            table_name="accounting_account",
            record_id=instance.pk,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )

    def perform_update(self, serializer):
        before = serialize_instance(serializer.instance)
        instance = serializer.save()
        log_audit(
            action=AuditLog.Action.UPDATE,
            table_name="accounting_account",
            record_id=instance.pk,
            before_data=before,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )

    def destroy(self, request, *args, **kwargs):
        # RF-CAT-06: Deactivate accounts that have no balance in the open period; never physically delete
        instance: Account = self.get_object()
        if instance.children.filter(is_active=True).exists():
            return Response(
                {"detail": "No se puede desactivar una cuenta que tiene subcuentas activas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        period = get_active_period()
        enriched, _ = _enrich_accounts([instance], period)
        current_balance = Decimal(enriched[0]["balance"])
        if current_balance != Decimal("0.00"):
            return Response(
                {
                    "detail": f"No se puede desactivar la cuenta {instance.code} porque tiene saldo distinto de cero (${current_balance:.2f}) en el período activo (RF-CAT-06)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        before = serialize_instance(instance)
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        log_audit(
            action=AuditLog.Action.DELETE,
            table_name="accounting_account",
            record_id=instance.pk,
            before_data=before,
            after_data=serialize_instance(instance),
            user=request.user,
        )
        return Response(AccountSerializer(instance).data, status=status.HTTP_200_OK)


class AccountMappingViewSet(viewsets.ModelViewSet):
    """Configurable event-to-account mapping for PostingService (RF-CAT-11, RN-12)."""

    queryset = AccountMapping.objects.select_related("account").order_by("key")
    serializer_class = AccountMappingSerializer
    permission_classes = [IsAccountantOrAdmin]
    pagination_class = None
    http_method_names = ["get", "patch", "put", "head", "options"]

    def perform_update(self, serializer):
        before = serialize_instance(serializer.instance)
        instance = serializer.save()
        log_audit(
            action=AuditLog.Action.UPDATE,
            table_name="accounting_account_mapping",
            record_id=None,
            before_data=before,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )


class JournalEntryViewSet(viewsets.ModelViewSet):
    """Libro Diario & Manual Journal Entries API (Vista 5 · RF-DIA-01..07)."""

    queryset = (
        JournalEntry.objects.select_related(
            "period",
            "created_by",
            "posted_by",
            "reversal_of",
            "reversed_by",
        )
        .prefetch_related("lines__account")
        .order_by("-entry_date", "-entry_number", "-id")
    )
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAccountantOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        period_id = params.get("period")
        if period_id:
            qs = qs.filter(period_id=period_id)

        entry_type = params.get("entry_type")
        if entry_type:
            qs = qs.filter(entry_type=entry_type)

        status_filter = params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        date_from = params.get("date_from")
        if date_from:
            qs = qs.filter(entry_date__gte=date_from)

        date_to = params.get("date_to")
        if date_to:
            qs = qs.filter(entry_date__lte=date_to)

        account_param = params.get("account")
        if account_param:
            if account_param.isdigit():
                qs = qs.filter(
                    Q(lines__account_id=int(account_param)) | Q(lines__account__code=account_param)
                ).distinct()
            else:
                qs = qs.filter(lines__account__code=account_param).distinct()

        search = (params.get("search") or "").strip()
        if search:
            q_filter = Q(description__icontains=search) | Q(lines__description__icontains=search)
            if search.isdigit():
                q_filter |= Q(entry_number=int(search)) | Q(lines__account__code__startswith=search)
            qs = qs.filter(q_filter).distinct()

        return qs

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        qs = self.get_queryset()
        posted_qs = qs.filter(status__in=[JournalEntry.EntryStatus.POSTED, JournalEntry.EntryStatus.REVERSED])
        agg = posted_qs.aggregate(
            sum_debit=Sum("total_debit"),
            sum_credit=Sum("total_credit"),
        )
        total_d = agg["sum_debit"] or Decimal("0.00")
        total_c = agg["sum_credit"] or Decimal("0.00")
        return Response(
            {
                "posted_count": qs.filter(status=JournalEntry.EntryStatus.POSTED).count(),
                "draft_count": qs.filter(status=JournalEntry.EntryStatus.DRAFT).count(),
                "reversed_count": qs.filter(status=JournalEntry.EntryStatus.REVERSED).count(),
                "total_debit": f"{total_d:.2f}",
                "total_credit": f"{total_c:.2f}",
                "is_balanced": total_d == total_c,
            }
        )

    def create(self, request, *args, **kwargs):
        write_ser = JournalEntryWriteSerializer(data=request.data)
        write_ser.is_valid(raise_exception=True)
        payload = write_ser.validated_data

        try:
            if payload.get("post_now"):
                entry = post_entry(
                    entry_date=payload["entry_date"],
                    description=payload["description"],
                    entry_type=payload.get("entry_type", JournalEntry.EntryType.MANUAL),
                    lines=payload["lines"],
                    user=request.user,
                )
            else:
                entry = create_draft_entry(
                    entry_date=payload["entry_date"],
                    description=payload["description"],
                    entry_type=payload.get("entry_type", JournalEntry.EntryType.MANUAL),
                    lines=payload["lines"],
                    user=request.user,
                )
        except (DjangoValidationError, ClosedPeriodError) as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        return Response(JournalEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        write_ser = JournalEntryWriteSerializer(data=request.data)
        write_ser.is_valid(raise_exception=True)
        payload = write_ser.validated_data

        try:
            entry = update_draft_entry(
                instance,
                entry_date=payload["entry_date"],
                description=payload["description"],
                lines=payload["lines"],
                user=request.user,
            )
            if payload.get("post_now"):
                entry = post_draft_entry(entry, user=request.user)
        except (DjangoValidationError, ClosedPeriodError) as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        return Response(JournalEntrySerializer(entry).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            delete_draft_entry(instance, user=request.user)
        except DjangoValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="post")
    def post_action(self, request, pk=None):
        instance = self.get_object()
        try:
            posted = post_draft_entry(instance, user=request.user)
        except (DjangoValidationError, ClosedPeriodError) as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response(JournalEntrySerializer(posted).data)

    @action(detail=True, methods=["post"], url_path="reverse")
    def reverse_action(self, request, pk=None):
        instance = self.get_object()
        reason = request.data.get("reason", "")
        reversal_date = request.data.get("reversal_date")
        try:
            reversal = reverse_entry(
                instance,
                reason=reason,
                user=request.user,
                reversal_date=reversal_date,
            )
        except (DjangoValidationError, ClosedPeriodError) as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response(JournalEntrySerializer(reversal).data, status=status.HTTP_201_CREATED)
