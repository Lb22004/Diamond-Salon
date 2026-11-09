from django.contrib import admin

from apps.sales.models import Customer, DocumentSeries, Sale, SaleLine, Service


class SaleLineInline(admin.TabularInline):
    model = SaleLine
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "customer_type", "document_type", "document_number", "nrc", "is_large_taxpayer", "is_active")
    list_filter = ("customer_type", "is_large_taxpayer", "is_active")
    search_fields = ("name", "document_number", "nrc")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "price", "income_account", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("code", "name")


@admin.register(DocumentSeries)
class DocumentSeriesAdmin(admin.ModelAdmin):
    list_display = ("doc_type", "prefix", "authorized_from", "authorized_to", "next_number", "is_active")
    list_filter = ("doc_type", "is_active")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("doc_number", "doc_type", "sale_date", "customer", "payment_method", "taxable_amount", "iva_amount", "total", "status")
    list_filter = ("doc_type", "status", "payment_method")
    search_fields = ("doc_number", "customer__name")
    inlines = [SaleLineInline]
