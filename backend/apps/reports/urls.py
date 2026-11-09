from django.urls import path

from apps.reports.views import (
    BookExportView,
    FinancialStatementsView,
    GeneralLedgerView,
    PeriodCloseView,
    TrialBalanceView,
)

urlpatterns = [
    path("ledger/", GeneralLedgerView.as_view(), name="general-ledger"),
    path("trial-balance/", TrialBalanceView.as_view(), name="trial-balance"),
    path("financial-statements/", FinancialStatementsView.as_view(), name="financial-statements"),
    path("periods/<int:pk>/close/", PeriodCloseView.as_view(), name="period-close"),
    path("exports/<str:book>/", BookExportView.as_view(), name="book-export"),
]
