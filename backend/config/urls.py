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
    # Each owner registers their module here, e.g.:
    # path("api/v1/accounting/", include("apps.accounting.urls")),
]
