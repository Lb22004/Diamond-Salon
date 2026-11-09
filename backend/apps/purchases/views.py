from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import ClosedPeriodError
from apps.purchases.models import Purchase, Supplier
from apps.purchases.serializers import (
    PurchaseSerializer,
    SupplierPaymentSerializer,
    SupplierSerializer,
)
from apps.purchases.services import (
    create_purchase,
    get_purchase_book,
    register_supplier_payment,
    void_purchase,
)


def _format_error(exc: Exception) -> str:
    if hasattr(exc, "message_dict"):
        return "; ".join(f"{k}: {', '.join(v)}" for k, v in exc.message_dict.items())
    if hasattr(exc, "messages") and exc.messages:
        return str(exc.messages[0])
    return str(exc)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by("name")
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1", "True"}:
            qs = qs.filter(is_active=True)
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(trade_name__icontains=search)
                | Q(brands_description__icontains=search)
                | Q(nrc__icontains=search)
                | Q(nit__icontains=search)
            )
        return qs


class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = (
        Purchase.objects.select_related("supplier", "period", "journal_entry", "created_by")
        .prefetch_related("lines__product", "lines__location", "payments")
        .order_by("doc_date", "id")
    )
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        period_id = self.request.query_params.get("period")
        supplier_id = self.request.query_params.get("supplier")
        destination = self.request.query_params.get("destination")
        status_param = self.request.query_params.get("status")
        search = self.request.query_params.get("search")

        if period_id:
            qs = qs.filter(period_id=period_id)
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if destination in {"VITRINA", "CABINA", "MIXED", "EXPENSE"}:
            qs = qs.filter(destination=destination)
        if status_param:
            qs = qs.filter(status=status_param)
        if search:
            qs = qs.filter(
                Q(doc_number__icontains=search)
                | Q(supplier__name__icontains=search)
                | Q(supplier__brands_description__icontains=search)
                | Q(notes__icontains=search)
            )
        return qs

    def create(self, request, *args, **kwargs):
        try:
            purchase = create_purchase(
                supplier_id=request.data.get("supplier") or request.data.get("supplier_id"),
                doc_type=request.data.get("doc_type", "CCF"),
                doc_number=request.data.get("doc_number", ""),
                doc_date=request.data.get("doc_date"),
                destination=request.data.get("destination", "VITRINA"),
                payment_condition=request.data.get("payment_condition", "CREDIT"),
                due_date=request.data.get("due_date") or None,
                lines=request.data.get("lines", []),
                apply_perception=bool(request.data.get("apply_perception", False)),
                notes=request.data.get("notes", ""),
                user=request.user,
            )
            return Response(self.get_serializer(purchase).data, status=status.HTTP_201_CREATED)
        except (DjangoValidationError, ClosedPeriodError) as exc:
            return Response({"detail": _format_error(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        purchase = self.get_object()
        try:
            updated = void_purchase(
                purchase=purchase,
                reason=request.data.get("reason", ""),
                user=request.user,
            )
            return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)
        except (DjangoValidationError, ClosedPeriodError) as exc:
            return Response({"detail": _format_error(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def payments(self, request, pk=None):
        purchase = self.get_object()
        try:
            payment = register_supplier_payment(
                purchase=purchase,
                payment_date=request.data.get("payment_date"),
                amount=request.data.get("amount"),
                payment_method=request.data.get("payment_method", "CASH"),
                reference=request.data.get("reference", ""),
                cash_account_id=request.data.get("cash_account_id"),
                user=request.user,
            )
            return Response(SupplierPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
        except (DjangoValidationError, ClosedPeriodError) as exc:
            return Response({"detail": _format_error(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseBookAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_purchase_book(
            period=request.query_params.get("period") or None,
            supplier_id=request.query_params.get("supplier") or None,
            destination=request.query_params.get("destination") or "",
            search=request.query_params.get("search") or "",
            date_from=request.query_params.get("date_from") or None,
            date_to=request.query_params.get("date_to") or None,
        )
        return Response(data)
