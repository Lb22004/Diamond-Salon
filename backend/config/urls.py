from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core.views import CustomTokenObtainPairView, health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.accounting.urls")),
    path("api/v1/accounting/", include("apps.accounting.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    path("api/v1/", include("apps.sales.urls")),
    path("api/v1/sales/", include("apps.sales.urls")),
    path("api/v1/inventory/", include("apps.inventory.urls")),
    path("api/v1/purchases/", include("apps.purchases.urls")),
    path("api/v1/", include("apps.inventory.urls")),
    path("api/v1/", include("apps.purchases.urls")),

    # Direct api prefixes for maximum backwards-compatibility with frontend calls
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.accounting.urls")),
    path("api/accounting/", include("apps.accounting.urls")),
    path("api/", include("apps.reports.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/", include("apps.sales.urls")),
    path("api/sales/", include("apps.sales.urls")),
    path("api/inventory/", include("apps.inventory.urls")),
    path("api/purchases/", include("apps.purchases.urls")),
    path("api/", include("apps.inventory.urls")),
    path("api/", include("apps.purchases.urls")),
]
