from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core.views import (
    AccountingPeriodViewSet,
    AuditLogViewSet,
    CompanyView,
    CustomTokenObtainPairView,
    DashboardSummaryView,
    EmployeeViewSet,
    FiscalYearViewSet,
    GlobalSearchView,
    MeView,
    NotificationsView,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("fiscal-years", FiscalYearViewSet, basename="fiscal-year")
router.register("periods", AccountingPeriodViewSet, basename="period")
router.register("audit-log", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("auth/token/", CustomTokenObtainPairView.as_view(), name="v1_token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="v1_token_refresh"),
    path("auth/me/", MeView.as_view(), name="v1_auth_me"),
    path("company/", CompanyView.as_view(), name="v1_company"),
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="v1_dashboard_summary"),
    path("search/", GlobalSearchView.as_view(), name="v1_global_search"),
    path("notifications/", NotificationsView.as_view(), name="v1_notifications"),
    path("", include(router.urls)),
]
