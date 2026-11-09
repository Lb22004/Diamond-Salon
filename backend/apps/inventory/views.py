from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import ClosedPeriodError
from apps.inventory.models import Category, Location, Product
from apps.inventory.serializers import CategorySerializer, LocationSerializer, ProductSerializer
from apps.inventory.services import (
    create_adjustment,
    get_inventory_summary,
    get_product_kardex,
    register_consumption,
    transfer_stock,
)


def _format_error(exc: Exception) -> str:
    if hasattr(exc, "message_dict"):
        return "; ".join(f"{k}: {', '.join(v)}" for k, v in exc.message_dict.items())
    if hasattr(exc, "messages") and exc.messages:
        return str(exc.messages[0])
    return str(exc)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.filter(is_active=True)
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related("category", "account", "default_supplier")
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        inv_type = self.request.query_params.get("inventory_type")
        if inv_type in ("VITRINA", "CABINA"):
            qs = qs.filter(inventory_type=inv_type)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(sku__icontains=search)
        return qs.order_by("id")

    @action(detail=True, methods=["get"], url_path="kardex")
    def kardex(self, request, pk=None):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        data = get_product_kardex(int(pk), date_from=date_from, date_to=date_to)
        return Response(data)


class InventorySummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search_vitrina = request.query_params.get("search_vitrina", "")
        search_cabina = request.query_params.get("search_cabina", "")
        location = request.query_params.get("location", "")
        data = get_inventory_summary(
            search_vitrina=search_vitrina,
            search_cabina=search_cabina,
            location=location,
        )
        return Response(data)


class InventoryAdjustmentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            adj = create_adjustment(
                adjustment_date=request.data.get("adjustment_date"),
                reason=request.data.get("reason", "PHYSICAL_COUNT"),
                lines=request.data.get("lines", []),
                notes=request.data.get("notes", ""),
                user=request.user,
            )
            return Response(
                {
                    "id": adj.id,
                    "adjustment_date": adj.adjustment_date.isoformat(),
                    "reason": adj.reason,
                    "journal_entry_id": adj.journal_entry_id,
                    "journal_entry_number": adj.journal_entry.entry_number if adj.journal_entry else None,
                },
                status=status.HTTP_201_CREATED,
            )
        except (DjangoValidationError, ClosedPeriodError) as exc:
            return Response({"detail": _format_error(exc)}, status=status.HTTP_400_BAD_REQUEST)


class InventoryConsumptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            cons = register_consumption(
                consumption_date=request.data.get("consumption_date"),
                location=request.data.get("location") or "CAB1",
                lines=request.data.get("lines", []),
                employee=request.data.get("employee"),
                sale_id=request.data.get("sale_id"),
                notes=request.data.get("notes", ""),
                user=request.user,
            )
            return Response(
                {
                    "id": cons.id,
                    "consumption_date": cons.consumption_date.isoformat(),
                    "location_id": cons.location_id,
                    "journal_entry_id": cons.journal_entry_id,
                    "journal_entry_number": cons.journal_entry.entry_number if cons.journal_entry else None,
                },
                status=status.HTTP_201_CREATED,
            )
        except (DjangoValidationError, ClosedPeriodError) as exc:
            return Response({"detail": _format_error(exc)}, status=status.HTTP_400_BAD_REQUEST)


class InventoryTransferAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            res = transfer_stock(
                transfer_date=request.data.get("transfer_date"),
                product=request.data.get("product") or request.data.get("product_id"),
                from_location=request.data.get("from_location"),
                to_location=request.data.get("to_location"),
                quantity=request.data.get("quantity"),
                target_product=request.data.get("target_product"),
                notes=request.data.get("notes", ""),
                user=request.user,
            )
            return Response(res, status=status.HTTP_201_CREATED)
        except (DjangoValidationError, ClosedPeriodError) as exc:
            return Response({"detail": _format_error(exc)}, status=status.HTTP_400_BAD_REQUEST)
