from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.sales.views import (
    CustomerViewSet,
    DocumentSeriesViewSet,
    SalesBookView,
    SaleViewSet,
    ServiceViewSet,
)

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"services", ServiceViewSet, basename="service")
router.register(r"document-series", DocumentSeriesViewSet, basename="document-series")
router.register(r"sales", SaleViewSet, basename="sale")

urlpatterns = [
    path("", include(router.urls)),
    path("sales-book/", SalesBookView.as_view(), name="sales-book"),
]
