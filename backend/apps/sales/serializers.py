from rest_framework import serializers

from apps.accounting.models import Account
from apps.sales.models import Customer, DocumentSeries, Sale, SaleLine, Service


class CustomerSerializer(serializers.ModelSerializer):
    customer_type_label = serializers.CharField(source="get_customer_type_display", read_only=True)
    document_type_label = serializers.CharField(source="get_document_type_display", read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "customer_type",
            "customer_type_label",
            "document_type",
            "document_type_label",
            "document_number",
            "nrc",
            "economic_activity",
            "is_large_taxpayer",
            "email",
            "phone",
            "address",
            "is_generic",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        c_type = attrs.get(
            "customer_type",
            self.instance.customer_type if self.instance else Customer.CustomerType.FINAL_CONSUMER,
        )
        nrc = attrs.get("nrc", self.instance.nrc if self.instance else None)
        doc_num = attrs.get("document_number", self.instance.document_number if self.instance else None)
        if c_type == Customer.CustomerType.TAXPAYER:
            if not nrc or not str(nrc).strip() or not doc_num or not str(doc_num).strip():
                raise serializers.ValidationError(
                    "Los clientes Contribuyente IVA requieren NIT/DUI y número de NRC obligatoriamente (RF-VEN-04)."
                )
        return attrs


class ServiceSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    income_account_code = serializers.CharField(source="income_account.code", read_only=True)
    income_account_name = serializers.CharField(source="income_account.name", read_only=True)
    income_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
    )

    class Meta:
        model = Service
        fields = [
            "id",
            "code",
            "name",
            "category",
            "category_label",
            "price",
            "income_account",
            "income_account_code",
            "income_account_name",
            "is_active",
        ]

    def validate(self, attrs):
        if not attrs.get("income_account") and not (self.instance and self.instance.income_account_id):
            acc_5101 = Account.objects.filter(code="5101").first()
            if acc_5101:
                attrs["income_account"] = acc_5101
        return attrs


class DocumentSeriesSerializer(serializers.ModelSerializer):
    doc_type_label = serializers.CharField(source="get_doc_type_display", read_only=True)
    next_formatted = serializers.CharField(read_only=True)

    class Meta:
        model = DocumentSeries
        fields = [
            "id",
            "doc_type",
            "doc_type_label",
            "prefix",
            "resolution",
            "authorized_from",
            "authorized_to",
            "next_number",
            "next_formatted",
            "valid_from",
            "is_active",
        ]


class SaleLineSerializer(serializers.ModelSerializer):
    regime_badge = serializers.CharField(read_only=True)
    service_code = serializers.CharField(source="service.code", read_only=True, default=None)

    class Meta:
        model = SaleLine
        fields = [
            "id",
            "line_no",
            "line_type",
            "regime_badge",
            "service",
            "service_code",
            "product_id",
            "description",
            "quantity",
            "unit_price",
            "discount",
            "taxable_amount",
            "iva_amount",
            "total",
            "unit_cost",
        ]


class SaleSerializer(serializers.ModelSerializer):
    doc_type_label = serializers.CharField(source="get_doc_type_display", read_only=True)
    payment_method_label = serializers.CharField(source="get_payment_method_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_nrc = serializers.CharField(source="customer.nrc", read_only=True)
    customer_document = serializers.CharField(source="customer.document_number", read_only=True)
    employee_name = serializers.SerializerMethodField()
    journal_entry_number = serializers.IntegerField(source="journal_entry.entry_number", read_only=True, default=None)
    lines = SaleLineSerializer(many=True, read_only=True)
    primary_regime = serializers.SerializerMethodField()
    concept_summary = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            "id",
            "series",
            "doc_type",
            "doc_type_label",
            "doc_number",
            "sale_date",
            "period",
            "customer",
            "customer_name",
            "customer_nrc",
            "customer_document",
            "employee",
            "employee_name",
            "payment_method",
            "payment_method_label",
            "taxable_amount",
            "exempt_amount",
            "non_subject_amount",
            "iva_amount",
            "iva_withheld",
            "total",
            "status",
            "status_label",
            "void_reason",
            "voided_at",
            "related_sale",
            "journal_entry",
            "journal_entry_number",
            "notes",
            "created_by",
            "created_at",
            "primary_regime",
            "concept_summary",
            "lines",
        ]

    def get_employee_name(self, obj: Sale) -> str | None:
        if not obj.employee:
            return None
        return obj.employee.full_name

    def get_primary_regime(self, obj: Sale) -> str:
        types = {ln.line_type for ln in obj.lines.all()}
        if types == {"SERVICE"}:
            return "CABINA"
        if types == {"PRODUCT"}:
            return "VITRINA"
        if len(types) > 1:
            return "MIXTO"
        return "CABINA"

    def get_concept_summary(self, obj: Sale) -> str:
        descs = [ln.description for ln in obj.lines.all()]
        if not descs:
            return obj.notes or "Venta en salón"
        return " · ".join(descs[:2]) + (f" (+{len(descs) - 2} más)" if len(descs) > 2 else "")
