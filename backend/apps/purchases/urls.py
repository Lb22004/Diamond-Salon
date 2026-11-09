from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.purchases.views import (
    PurchaseBookAPIView,
    PurchaseViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register(r"suppliers", SupplierViewSet, basename="supplier")
router.register(r"purchases", PurchaseViewSet, basename="purchase")

urlpatterns = [
    path("purchase-book/", PurchaseBookAPIView.as_view(), name="purchase-book"),
    path("", include(router.urls)),
]
