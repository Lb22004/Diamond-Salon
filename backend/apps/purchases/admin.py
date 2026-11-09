from django.contrib import admin

from apps.purchases.models import Purchase, PurchaseLine, Supplier, SupplierPayment


class PurchaseLineInline(admin.TabularInline):
    model = PurchaseLine
    extra = 0


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "trade_name", "nrc", "nit", "taxpayer_category", "is_active")
    search_fields = ("name", "trade_name", "nrc", "nit")


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("doc_type", "doc_number", "doc_date", "supplier", "destination", "total", "payment_status", "status")
    list_filter = ("destination", "payment_status", "status", "doc_type", "period")
    search_fields = ("doc_number", "supplier__name")
    inlines = [PurchaseLineInline]


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = ("purchase", "payment_date", "amount", "payment_method", "reference")
