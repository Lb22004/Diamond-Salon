from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import ClosedPeriodError
from apps.core.models import AccountingPeriod, AuditLog
from apps.core.permissions import IsCashierOrAdmin
from apps.core.services.audit import log_audit, serialize_instance
from apps.core.services.periods import get_active_period
from apps.sales.models import Customer, DocumentSeries, Sale, Service
from apps.sales.serializers import (
    CustomerSerializer,
    DocumentSeriesSerializer,
    SaleSerializer,
    ServiceSerializer,
)
from apps.sales.services import (
    create_sale,
    get_available_vitrina_products,
    get_sales_book,
    void_sale,
)


def _resolve_period(request) -> AccountingPeriod | None:
    p_param = request.query_params.get("period")
    if p_param:
        s = str(p_param).strip()
        if s.isdigit():
            p = AccountingPeriod.objects.filter(pk=int(s)).first()
            if p:
                return p
        if "-" in s:
            parts = s.split("-", 1)
            if parts[0].isdigit() and parts[1].isdigit():
                p = AccountingPeriod.objects.filter(year=int(parts[0]), month=int(parts[1])).first()
                if p:
                    return p
    return getattr(request, "active_period", None) or get_active_period()


class CustomerViewSet(viewsets.ModelViewSet):
    """Customer CRUD endpoint (`/api/v1/customers/` · RF-VEN-13)."""

    queryset = Customer.objects.all().order_by("-is_generic", "name")
    serializer_class = CustomerSerializer
    permission_classes = [IsCashierOrAdmin]
    filterset_fields = ["customer_type", "is_large_taxpayer", "is_active"]
    search_fields = ["name", "document_number", "nrc", "email"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            action=AuditLog.Action.CREATE,
            table_name="sales_customer",
            record_id=instance.pk,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )

    def perform_update(self, serializer):
        before = serialize_instance(serializer.instance)
        instance = serializer.save()
        log_audit(
            action=AuditLog.Action.UPDATE,
            table_name="sales_customer",
            record_id=instance.pk,
            before_data=before,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )


class ServiceViewSet(viewsets.ModelViewSet):
    """Beauty Services Catalog CRUD (`/api/v1/services/` · RF-VEN-13)."""

    queryset = Service.objects.select_related("income_account").all().order_by("code")
    serializer_class = ServiceSerializer
    permission_classes = [IsCashierOrAdmin]
    filterset_fields = ["category", "is_active"]
    search_fields = ["code", "name"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            action=AuditLog.Action.CREATE,
            table_name="sales_service",
            record_id=instance.pk,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )

    def perform_update(self, serializer):
        before = serialize_instance(serializer.instance)
        instance = serializer.save()
        log_audit(
            action=AuditLog.Action.UPDATE,
            table_name="sales_service",
            record_id=instance.pk,
            before_data=before,
            after_data=serialize_instance(instance),
            user=self.request.user,
        )


class DocumentSeriesViewSet(viewsets.ModelViewSet):
    """Authorized Fiscal Document Series (`/api/v1/document-series/` · RF-VEN-02)."""

    queryset = DocumentSeries.objects.all().order_by("doc_type", "id")
    serializer_class = DocumentSeriesSerializer
    permission_classes = [IsCashierOrAdmin]
    filterset_fields = ["doc_type", "is_active"]


class SaleViewSet(viewsets.ReadOnlyModelViewSet):
    """Sales listing, creation, and voiding (`/api/v1/sales/` · RF-VEN-01..11)."""

    queryset = (
        Sale.objects.select_related("customer", "employee", "series", "journal_entry", "period")
        .prefetch_related("lines__service")
        .all()
        .order_by("-sale_date", "-id")
    )
    serializer_class = SaleSerializer
    permission_classes = [IsCashierOrAdmin]
    filterset_fields = ["period", "doc_type", "status", "payment_method", "customer"]
    search_fields = ["doc_number", "customer__name", "notes"]

    def create(self, request, *args, **kwargs):
        data = request.data
        try:
            sale = create_sale(
                sale_date=data.get("sale_date"),
                doc_type=data.get("doc_type", "FCF"),
                customer=data.get("customer"),
                payment_method=data.get("payment_method", Sale.PaymentMethod.CASH),
                lines=data.get("lines", []),
                employee=data.get("employee"),
                related_sale=data.get("related_sale"),
                notes=data.get("notes", ""),
                user=request.user,
            )
        except (DjangoValidationError, ClosedPeriodError) as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="void")
    def void(self, request, pk=None):
        sale = self.get_object()
        reason = request.data.get("reason", "")
        try:
            voided = void_sale(sale, reason=reason, user=request.user)
        except (DjangoValidationError, ClosedPeriodError) as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SaleSerializer(voided).data, status=status.HTTP_200_OK)


class SalesBookView(APIView):
    """GET /api/v1/sales-book/?period=&doc_type=&line_type=&search=&date_from=&date_to="""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        period = _resolve_period(request)
        doc_type = request.query_params.get("doc_type") or request.query_params.get("type")
        line_type = request.query_params.get("line_type")
        search = request.query_params.get("search")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        data = get_sales_book(
            period=period,
            doc_type=doc_type,
            line_type=line_type,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
        data["vitrina_products"] = get_available_vitrina_products()
        return Response(data)
