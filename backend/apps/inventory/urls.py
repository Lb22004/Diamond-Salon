from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inventory.views import (
    CategoryViewSet,
    InventoryAdjustmentAPIView,
    InventoryConsumptionAPIView,
    InventorySummaryAPIView,
    InventoryTransferAPIView,
    LocationViewSet,
    ProductViewSet,
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="inventory-categories")
router.register(r"locations", LocationViewSet, basename="inventory-locations")
router.register(r"products", ProductViewSet, basename="inventory-products")

urlpatterns = [
    path("", include(router.urls)),
    path("inventory/summary/", InventorySummaryAPIView.as_view(), name="inventory-summary"),
    path("inventory/adjustments/", InventoryAdjustmentAPIView.as_view(), name="inventory-adjustments"),
    path("inventory/consumptions/", InventoryConsumptionAPIView.as_view(), name="inventory-consumptions"),
    path("inventory/transfers/", InventoryTransferAPIView.as_view(), name="inventory-transfers"),
]
