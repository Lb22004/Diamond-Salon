from django.contrib import admin

from apps.accounting.models import (
    Account,
    AccountMapping,
    JournalEntry,
    JournalEntryLine,
    PeriodBalance,
)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "level",
        "account_type",
        "nature",
        "accepts_entries",
        "inventory_type",
        "is_active",
    )
    list_filter = ("level", "account_type", "nature", "accepts_entries", "inventory_type", "is_active")
    search_fields = ("code", "name", "classification")


@admin.register(AccountMapping)
class AccountMappingAdmin(admin.ModelAdmin):
    list_display = ("key", "account", "description")
    search_fields = ("key", "description", "account__code", "account__name")


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 0


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "period",
        "entry_number",
        "entry_date",
        "entry_type",
        "status",
        "total_debit",
        "total_credit",
        "created_by",
    )
    list_filter = ("status", "entry_type", "period")
    search_fields = ("description",)
    inlines = [JournalEntryLineInline]


@admin.register(PeriodBalance)
class PeriodBalanceAdmin(admin.ModelAdmin):
    list_display = ("period", "account", "opening_balance", "debit_total", "credit_total", "closing_balance")
    list_filter = ("period",)
