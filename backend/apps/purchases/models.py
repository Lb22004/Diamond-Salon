from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Supplier(models.Model):
    class TaxpayerCategory(models.TextChoices):
        SMALL = "SMALL", "Pequeño Contribuyente"
        MEDIUM = "MEDIUM", "Mediano Contribuyente"
        LARGE = "LARGE", "Gran Contribuyente (Percepción 1%)"
        EXCLUDED = "EXCLUDED", "Sujeto Excluido"

    name = models.CharField(max_length=150)
    trade_name = models.CharField(max_length=150, null=True, blank=True)
    nit = models.CharField(max_length=17, unique=True)
    nrc = models.CharField(max_length=10, null=True, blank=True)
    taxpayer_category = models.CharField(
        max_length=10,
        choices=TaxpayerCategory.choices,
        default=TaxpayerCategory.MEDIUM,
    )
    brands_description = models.CharField(max_length=200, null=True, blank=True)
    contact_name = models.CharField(max_length=120, null=True, blank=True)
    phone = models.CharField(max_length=30, null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "purchases_supplier"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(taxpayer_category__in=["SMALL", "MEDIUM", "LARGE", "EXCLUDED"]),
                name="ck_purchases_supplier_category",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.nit})"


class Purchase(models.Model):
    class DocType(models.TextChoices):
        CCF = "CCF", "Comprobante de Crédito Fiscal (CCF)"
        INVOICE = "INVOICE", "Factura de Consumidor Final"
        NC = "NC", "Nota de Crédito"
        ND = "ND", "Nota de Débito"
        IMPORT = "IMPORT", "Declaración de Mercancías (Importación)"
        EXCLUDED_SUBJECT = "EXCLUDED_SUBJECT", "Factura de Sujeto Excluido"

    class Destination(models.TextChoices):
        VITRINA = "VITRINA", "Vitrina (Reventa)"
        CABINA = "CABINA", "Cabina (Servicio)"
        MIXED = "MIXED", "Mixto (Vitrina y Cabina)"
        EXPENSE = "EXPENSE", "Gasto Operativo / Administrativo"

    class PaymentCondition(models.TextChoices):
        CASH = "CASH", "Contado"
        CREDIT = "CREDIT", "Crédito"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        PARTIAL = "PARTIAL", "Abono Parcial"
        PAID = "PAID", "Liquidado"

    class Status(models.TextChoices):
        REGISTERED = "REGISTERED", "Registrado"
        VOIDED = "VOIDED", "Anulado"

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchases",
    )
    doc_type = models.CharField(max_length=16, choices=DocType.choices, default=DocType.CCF)
    doc_number = models.CharField(max_length=30)
    doc_date = models.DateField()
    period = models.ForeignKey(
        "core.AccountingPeriod",
        on_delete=models.PROTECT,
        related_name="purchases",
    )
    destination = models.CharField(
        max_length=10,
        choices=Destination.choices,
        default=Destination.VITRINA,
    )
    taxable_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    exempt_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    iva_credit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    iva_perceived = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    payment_condition = models.CharField(
        max_length=6,
        choices=PaymentCondition.choices,
        default=PaymentCondition.CREDIT,
    )
    due_date = models.DateField(null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    payment_status = models.CharField(
        max_length=8,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.REGISTERED,
    )
    void_reason = models.CharField(max_length=255, null=True, blank=True)
    journal_entry = models.ForeignKey(
        "accounting.JournalEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchases",
    )
    notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchases_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "purchases_purchase"
        ordering = ["doc_date", "id"]
        indexes = [
            models.Index(fields=["doc_date"], name="ix_purchase_date"),
            models.Index(fields=["period"], name="ix_purchase_period"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "doc_type", "doc_number"],
                name="ux_purchases_supplier_doc",
            ),
            models.CheckConstraint(
                condition=Q(taxable_amount__gte=0)
                & Q(exempt_amount__gte=0)
                & Q(iva_credit__gte=0)
                & Q(iva_perceived__gte=0)
                & Q(total__gte=0)
                & Q(amount_paid__gte=0),
                name="ck_purchases_amounts_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(amount_paid__lte=F("total")),
                name="ck_purchases_paid_lte_total",
            ),
            models.CheckConstraint(
                condition=Q(payment_condition="CASH") | Q(due_date__isnull=False),
                name="ck_purchases_credit_requires_due_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.doc_type} {self.doc_number} - {self.supplier.name}"


class PurchaseLine(models.Model):
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    line_no = models.SmallIntegerField()
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchase_lines",
    )
    expense_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expense_purchase_lines",
    )
    location = models.ForeignKey(
        "inventory.Location",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchase_lines",
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=4)
    taxable_amount = models.DecimalField(max_digits=14, decimal_places=2)
    iva_amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = "purchases_purchase_line"
        ordering = ["line_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["purchase", "line_no"],
                name="ux_purchases_line_no",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0) & Q(unit_cost__gte=0) & Q(taxable_amount__gte=0) & Q(iva_amount__gte=0),
                name="ck_purchases_line_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(product__isnull=False, expense_account__isnull=True)
                    | Q(product__isnull=True, expense_account__isnull=False)
                ),
                name="ck_purchases_line_product_xor_expense",
            ),
            models.CheckConstraint(
                condition=Q(product__isnull=True) | Q(location__isnull=False),
                name="ck_purchases_line_product_requires_location",
            ),
        ]


class SupplierPayment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Efectivo (Caja General 110101)"
        TRANSFER = "TRANSFER", "Transferencia Bancaria (110102)"
        CHECK = "CHECK", "Cheque (110102)"
        CARD = "CARD", "Tarjeta Corporativa (110102)"

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    reference = models.CharField(max_length=60, null=True, blank=True)
    cash_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        related_name="supplier_payments",
    )
    journal_entry = models.ForeignKey(
        "accounting.JournalEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="supplier_payments",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supplier_payments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "purchases_supplier_payment"
        ordering = ["-payment_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="ck_purchases_payment_positive",
            ),
        ]
