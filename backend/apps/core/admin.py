from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AccountingPeriod, AuditLog, Company, Employee, FiscalYear, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Rol", {"fields": ("role",)}),)
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("trade_name", "legal_name", "nit", "nrc", "iva_rate", "currency", "allow_negative_stock")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "position", "is_active")
    list_filter = ("position", "is_active")


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ("year", "start_date", "end_date", "status")


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "start_date", "end_date", "status", "is_active", "closed_at", "closed_by")
    list_filter = ("year", "status", "is_active")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "table_name", "record_id", "ip_address")
    list_filter = ("action", "table_name")
    readonly_fields = ("user", "action", "table_name", "record_id", "before_data", "after_data", "ip_address", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
