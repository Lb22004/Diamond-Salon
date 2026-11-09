from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AccountingPeriod
from apps.core.permissions import IsAccountantOrAdmin
from apps.core.services.periods import get_active_period
from apps.reports.services import (
    close_period,
    export_book,
    get_account_ledger,
    get_close_preview,
    get_financial_statements,
    get_trial_balance,
)


class IgnoreClientContentNegotiation(BaseContentNegotiation):
    """Bypass DRF's ?format= query param interception so ?format=pdf|xlsx works cleanly."""

    def select_parser(self, request, parsers):
        return parsers[0] if parsers else None

    def select_renderer(self, request, renderers, format_suffix=None):
        return (renderers[0], renderers[0].media_type)


def _resolve_period_from_request(request) -> AccountingPeriod | None:
    period_param = request.query_params.get("period")
    if period_param:
        p_str = str(period_param).strip()
        if p_str.isdigit():
            p = AccountingPeriod.objects.filter(pk=int(p_str)).first()
            if p:
                return p
        if "-" in p_str:
            parts = p_str.split("-", 1)
            if parts[0].isdigit() and parts[1].isdigit():
                p = AccountingPeriod.objects.filter(year=int(parts[0]), month=int(parts[1])).first()
                if p:
                    return p
    return getattr(request, "active_period", None) or get_active_period()


class GeneralLedgerView(APIView):
    """GET /api/v1/ledger/?account=110101&period=<id>&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        period = _resolve_period_from_request(request)
        account_param = request.query_params.get("account")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        data = get_account_ledger(
            account_identifier=account_param,
            period=period,
            date_from=date_from,
            date_to=date_to,
        )
        return Response(data)


class TrialBalanceView(APIView):
    """GET /api/v1/trial-balance/?period=<id>"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        period = _resolve_period_from_request(request)
        data = get_trial_balance(period=period)
        return Response(data)


class FinancialStatementsView(APIView):
    """GET /api/v1/financial-statements/?period=<id>"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        period = _resolve_period_from_request(request)
        data = get_financial_statements(period=period)
        return Response(data)


class PeriodCloseView(APIView):
    """
    GET  /api/v1/periods/<pk>/close/ -> Pre-close checklist & IVA liquidation preview (RF-CIE-02..03)
    POST /api/v1/periods/<pk>/close/ -> Execute monthly closing & snapshot balances (RF-CIE-03..04)
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAccountantOrAdmin()]
        return [permissions.IsAuthenticated()]

    def get(self, request, pk: int):
        period = get_object_or_404(AccountingPeriod, pk=pk)
        return Response(get_close_preview(period))

    def post(self, request, pk: int):
        period = get_object_or_404(AccountingPeriod, pk=pk)
        post_iva = bool(request.data.get("post_iva_liquidation", True))
        try:
            result = close_period(
                period,
                user=request.user,
                post_iva_liquidation=post_iva,
            )
        except DjangoValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class BookExportView(APIView):
    """GET /api/v1/exports/<book>/?format=pdf|xlsx&period=<id>&account=<code>"""

    permission_classes = [permissions.IsAuthenticated]
    content_negotiation_class = IgnoreClientContentNegotiation

    def get(self, request, book: str):
        period = _resolve_period_from_request(request)
        fmt = (
            request.query_params.get("format")
            or request.query_params.get("export_format")
            or "pdf"
        )
        account = request.query_params.get("account")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        payload, content_type, filename = export_book(
            book=book,
            fmt=fmt,
            period=period,
            account=account,
            date_from=date_from,
            date_to=date_to,
            user=request.user,
        )
        response = HttpResponse(payload, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
