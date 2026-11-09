from decimal import Decimal

from django.db import models
from django.db.models import F, Q


class Customer(models.Model):
    """Salon client / customer (`sales_customer` · RF-VEN-04, RF-VEN-13)."""

    class CustomerType(models.TextChoices):
        FINAL_CONSUMER = "FINAL_CONSUMER", "Consumidor Final"
        TAXPAYER = "TAXPAYER", "Contribuyente IVA"

    class DocumentType(models.TextChoices):
        DUI = "DUI", "DUI"
        NIT = "NIT", "NIT"
        PASSPORT = "PASSPORT", "Pasaporte"
        OTHER = "OTHER", "Otro"

    name = models.CharField(max_length=150)
    customer_type = models.CharField(
        max_length=15,
        choices=CustomerType.choices,
        default=CustomerType.FINAL_CONSUMER,
    )
    document_type = models.CharField(
        max_length=10,
        choices=DocumentType.choices,
        null=True,
        blank=True,
    )
    document_number = models.CharField(max_length=20, null=True, blank=True)
    nrc = models.CharField(max_length=10, null=True, blank=True)
    economic_activity = models.CharField(max_length=150, null=True, blank=True)
    is_large_taxpayer = models.BooleanField(default=False)
    email = models.EmailField(max_length=254, null=True, blank=True)
    phone = models.CharField(max_length=30, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    is_generic = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sales_customer"
        ordering = ["-is_generic", "name"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~Q(customer_type="TAXPAYER")
                    | (
                        Q(nrc__isnull=False)
                        & ~Q(nrc="")
                        & Q(document_number__isnull=False)
                        & ~Q(document_number="")
                    )
                ),
                name="ck_sales_customer_taxpayer_ids",
            ),
            models.UniqueConstraint(
                fields=["document_type", "document_number"],
                condition=Q(document_number__isnull=False) & ~Q(document_number=""),
                name="ux_customer_document",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_customer_type_display()})"


class Service(models.Model):
    """Beauty & styling service catalog (`sales_service` · RF-VEN-01, RF-VEN-13)."""

    class Category(models.TextChoices):
        HAIRCUT = "HAIRCUT", "Corte"
        STYLING = "STYLING", "Peinado & Brushing"
        COLOR = "COLOR", "Colorimetría"
        TREATMENT = "TREATMENT", "Tratamiento Capilar"
        NAILS = "NAILS", "Uñas & Spa"
        OTHER = "OTHER", "Otro Servicio"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.STYLING,
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Precio de lista con IVA incluido (13%)",
    )
    income_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        related_name="services",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "sales_service"
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gte=0),
                name="ck_sales_service_price_nonneg",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} · {self.name} (${self.price:.2f})"


class ServiceSupply(models.Model):
    """Optional recipe of Cabina supplies consumed per service (`sales_service_supply` · RF-INV-10)."""

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="supplies",
    )
    product_id = models.BigIntegerField(db_column="product_id")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        db_table = "sales_service_supply"
        constraints = [
            models.UniqueConstraint(
                fields=["service", "product_id"],
                name="ux_sales_service_supply_unique",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="ck_sales_service_supply_qty_pos",
            ),
        ]


class DocumentSeries(models.Model):
    """Authorized fiscal document correlative series (`sales_document_series` · RF-VEN-02, RN-09)."""

    class DocType(models.TextChoices):
        FCF = "FCF", "Factura Consumidor Final (FCF)"
        CCF = "CCF", "Comprobante de Crédito Fiscal (CCF)"
        NC = "NC", "Nota de Crédito (NC)"
        ND = "ND", "Nota de Débito (ND)"

    doc_type = models.CharField(max_length=3, choices=DocType.choices)
    prefix = models.CharField(max_length=10)
    resolution = models.CharField(max_length=60, null=True, blank=True)
    authorized_from = models.IntegerField(default=1)
    authorized_to = models.IntegerField(default=9999)
    next_number = models.IntegerField(default=1)
    valid_from = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "sales_document_series"
        ordering = ["doc_type", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(authorized_from__gt=0) & Q(authorized_to__gte=F("authorized_from")),
                name="ck_sales_series_range",
            ),
            models.UniqueConstraint(
                fields=["doc_type"],
                condition=Q(is_active=True),
                name="ux_series_active",
            ),
        ]

    @property
    def next_formatted(self) -> str:
        return f"{self.prefix}{self.next_number:04d}"

    def __str__(self) -> str:
        return f"{self.doc_type} ({self.prefix}{self.authorized_from:04d}..{self.authorized_to:04d})"


class Sale(models.Model):
    """Issued fiscal sale header (`sales_sale` · RF-VEN-01..12)."""

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Efectivo (Caja)"
        CARD = "CARD", "Tarjeta POS (Banco)"
        TRANSFER = "TRANSFER", "Transferencia Bancaria"
        CREDIT = "CREDIT", "Crédito Cliente (CxC)"

    class SaleStatus(models.TextChoices):
        ISSUED = "ISSUED", "Emitida"
        VOIDED = "VOIDED", "Anulada"

    series = models.ForeignKey(
        DocumentSeries,
        on_delete=models.PROTECT,
        related_name="sales",
    )
    doc_type = models.CharField(max_length=3, choices=DocumentSeries.DocType.choices)
    doc_number = models.CharField(max_length=20)
    sale_date = models.DateField()
    period = models.ForeignKey(
        "core.AccountingPeriod",
        on_delete=models.PROTECT,
        related_name="sales",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="sales",
    )
    employee = models.ForeignKey(
        "core.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    taxable_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    exempt_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    non_subject_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    iva_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    iva_withheld = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(
        max_length=10,
        choices=SaleStatus.choices,
        default=SaleStatus.ISSUED,
    )
    void_reason = models.CharField(max_length=255, null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    related_sale = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="adjustments",
    )
    journal_entry = models.ForeignKey(
        "accounting.JournalEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_documents",
    )
    notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.PROTECT,
        related_name="created_sales",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sales_sale"
        ordering = ["-sale_date", "-id"]
        indexes = [
            models.Index(fields=["sale_date"], name="ix_sale_date"),
            models.Index(fields=["period", "doc_type"], name="ix_sale_period"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["doc_type", "doc_number"],
                name="ux_sales_doc_type_number",
            ),
            models.CheckConstraint(
                condition=Q(taxable_amount__gte=0)
                & Q(exempt_amount__gte=0)
                & Q(non_subject_amount__gte=0)
                & Q(iva_amount__gte=0)
                & Q(iva_withheld__gte=0)
                & Q(total__gte=0),
                name="ck_sales_sale_amounts_nonneg",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.doc_type} {self.doc_number} (${self.total:.2f})"


class SaleLine(models.Model):
    """Individual service or retail product line on a Sale (`sales_sale_line` · RF-VEN-01, RF-VEN-05)."""

    class LineType(models.TextChoices):
        SERVICE = "SERVICE", "Servicio en Salón (Cabina)"
        PRODUCT = "PRODUCT", "Producto Retail (Vitrina)"

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    line_no = models.SmallIntegerField()
    line_type = models.CharField(max_length=10, choices=LineType.choices)
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sale_lines",
    )
    product_id = models.BigIntegerField(null=True, blank=True, db_column="product_id")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("1.000"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    taxable_amount = models.DecimalField(max_digits=14, decimal_places=2)
    iva_amount = models.DecimalField(max_digits=14, decimal_places=2)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Costo promedio ponderado unitario al momento de la venta (solo VITRINA)",
    )

    class Meta:
        db_table = "sales_sale_line"
        ordering = ["sale", "line_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["sale", "line_no"],
                name="ux_sales_sale_line_no",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0)
                & Q(unit_price__gte=0)
                & Q(discount__gte=0)
                & Q(taxable_amount__gte=0)
                & Q(iva_amount__gte=0)
                & Q(total__gte=0),
                name="ck_sales_line_amounts_nonneg",
            ),
        ]

    @property
    def regime_badge(self) -> str:
        return "CABINA" if self.line_type == self.LineType.SERVICE else "VITRINA"
