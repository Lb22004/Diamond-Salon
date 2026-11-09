from decimal import Decimal
from rest_framework import serializers

from apps.purchases.models import Purchase, PurchaseLine, Supplier, SupplierPayment


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "trade_name",
            "nit",
            "nrc",
            "taxpayer_category",
            "brands_description",
            "contact_name",
            "phone",
            "email",
            "address",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PurchaseLineSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True, default="")
    product_name = serializers.CharField(source="product.name", read_only=True, default="")
    location_name = serializers.CharField(source="location.name", read_only=True, default="")

    class Meta:
        model = PurchaseLine
        fields = [
            "id",
            "line_no",
            "product",
            "product_sku",
            "product_name",
            "expense_account",
            "location",
            "location_name",
            "description",
            "quantity",
            "unit_cost",
            "taxable_amount",
            "iva_amount",
        ]


class SupplierPaymentSerializer(serializers.ModelSerializer):
    cash_account_code = serializers.CharField(source="cash_account.code", read_only=True, default="")
    journal_entry_number = serializers.IntegerField(source="journal_entry.entry_number", read_only=True, default=None)

    class Meta:
        model = SupplierPayment
        fields = [
            "id",
            "purchase",
            "payment_date",
            "amount",
            "payment_method",
            "reference",
            "cash_account",
            "cash_account_code",
            "journal_entry",
            "journal_entry_number",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "purchase", "cash_account", "journal_entry", "created_by", "created_at"]


class PurchaseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    supplier_brands = serializers.CharField(source="supplier.brands_description", read_only=True, default="")
    supplier_nrc = serializers.CharField(source="supplier.nrc", read_only=True, default="")
    supplier_nit = serializers.CharField(source="supplier.nit", read_only=True)
    journal_entry_number = serializers.IntegerField(source="journal_entry.entry_number", read_only=True, default=None)
    lines = PurchaseLineSerializer(many=True, read_only=True)
    payments = SupplierPaymentSerializer(many=True, read_only=True)
    balance_due = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = [
            "id",
            "supplier",
            "supplier_name",
            "supplier_brands",
            "supplier_nrc",
            "supplier_nit",
            "doc_type",
            "doc_number",
            "doc_date",
            "period",
            "destination",
            "taxable_amount",
            "exempt_amount",
            "iva_credit",
            "iva_perceived",
            "total",
            "payment_condition",
            "due_date",
            "amount_paid",
            "balance_due",
            "payment_status",
            "status",
            "void_reason",
            "journal_entry",
            "journal_entry_number",
            "notes",
            "lines",
            "payments",
            "created_by",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "period",
            "taxable_amount",
            "exempt_amount",
            "iva_credit",
            "iva_perceived",
            "total",
            "amount_paid",
            "payment_status",
            "status",
            "void_reason",
            "journal_entry",
            "created_by",
            "created_at",
        ]

    def get_balance_due(self, obj) -> str:
        bal = max(Decimal("0.00"), obj.total - obj.amount_paid)
        return f"{bal:.2f}"
