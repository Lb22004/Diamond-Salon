from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounting.views import (
    AccountMappingViewSet,
    AccountViewSet,
    JournalEntryViewSet,
)

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("account-mappings", AccountMappingViewSet, basename="account-mapping")
router.register("journal-entries", JournalEntryViewSet, basename="journal-entry")

urlpatterns = [
    path("", include(router.urls)),
]
