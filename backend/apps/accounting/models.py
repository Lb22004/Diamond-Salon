from decimal import Decimal

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q


class Account(models.Model):
    """Hierarchical Chart of Accounts under NIIF para las PYMES (Vista 1 · RF-CAT)."""

    class AccountType(models.TextChoices):
        ASSET = "ASSET", "Activo"
        LIABILITY = "LIABILITY", "Pasivo"
        EQUITY = "EQUITY", "Patrimonio"
        COST = "COST", "Costo"
        EXPENSE = "EXPENSE", "Gasto"
        INCOME = "INCOME", "Ingreso"
        CLOSING = "CLOSING", "Cierre"

    class Nature(models.TextChoices):
        DEBIT = "DEBIT", "Deudora"
        CREDIT = "CREDIT", "Acreedora"

    class InventoryRegime(models.TextChoices):
        VITRINA = "VITRINA", "Vitrina (Venta)"
        CABINA = "CABINA", "Cabina (Servicio)"

    LEVEL_LABELS = {
        1: "Clase",
        2: "Grupo",
        3: "Cuenta mayor",
        4: "Subcuenta analítica",
        5: "Auxiliar",
        6: "Detalle",
    }

    code = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r"^[0-9]+$", "El código contable debe contener únicamente dígitos.")],
    )
    name = models.CharField(max_length=150)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    level = models.SmallIntegerField()
    account_type = models.CharField(max_length=10, choices=AccountType.choices)
    nature = models.CharField(max_length=6, choices=Nature.choices)
    classification = models.CharField(max_length=40, blank=True, default="")
    accepts_entries = models.BooleanField(default=False)
    inventory_type = models.CharField(
        max_length=10,
        choices=InventoryRegime.choices,
        null=True,
        blank=True,
    )
    niif_reference = models.CharField(max_length=60, blank=True, default="")
    debit_rule = models.TextField(blank=True, default="")
    credit_rule = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounting_account"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["parent"], name="ix_account_parent"),
            models.Index(fields=["code"], name="ix_account_code_prefix"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(level__gte=1, level__lte=6),
                name="ck_accounting_account_level",
            ),
            models.CheckConstraint(
                condition=Q(
                    account_type__in=["ASSET", "LIABILITY", "EQUITY", "COST", "EXPENSE", "INCOME", "CLOSING"]
                ),
                name="ck_accounting_account_type",
            ),
            models.CheckConstraint(
                condition=Q(nature__in=["DEBIT", "CREDIT"]),
                name="ck_accounting_account_nature",
            ),
            models.CheckConstraint(
                condition=Q(inventory_type__isnull=True) | Q(inventory_type__in=["VITRINA", "CABINA"]),
                name="ck_accounting_account_inv_type",
            ),
            models.CheckConstraint(
                condition=(Q(level=1) & Q(parent__isnull=True))
                | (Q(level__gt=1) & Q(parent__isnull=False)),
                name="ck_accounting_account_root_parent",
            ),
        ]

    @property
    def level_label(self) -> str:
        return self.LEVEL_LABELS.get(self.level, f"Nivel {self.level}")

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class AccountMapping(models.Model):
    """Configurable business-event to account mapping used by PostingService (RN-12, RF-CAT-11)."""

    key = models.CharField(max_length=40, primary_key=True)
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="mappings",
    )
    description = models.CharField(max_length=200)

    class Meta:
        db_table = "accounting_account_mapping"
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.key} -> {self.account.code} ({self.account.name})"


class JournalEntry(models.Model):
    """Double-entry journal entry header / 'Partida' (Vista 5 · Libro diario · RF-DIA)."""

    class EntryType(models.TextChoices):
        OPENING = "OPENING", "Apertura"
        MANUAL = "MANUAL", "Manual"
        SALE = "SALE", "Venta"
        PURCHASE = "PURCHASE", "Compra"
        PAYMENT = "PAYMENT", "Pago"
        INVENTORY = "INVENTORY", "Inventario"
        ADJUSTMENT = "ADJUSTMENT", "Ajuste"
        CLOSING = "CLOSING", "Cierre"
        REVERSAL = "REVERSAL", "Reversión"

    class EntryStatus(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        POSTED = "POSTED", "Mayorizada"
        REVERSED = "REVERSED", "Revertida"

    period = models.ForeignKey(
        "core.AccountingPeriod",
        on_delete=models.PROTECT,
        related_name="journal_entries",
    )
    entry_number = models.IntegerField(null=True, blank=True)
    entry_date = models.DateField()
    description = models.TextField()
    entry_type = models.CharField(
        max_length=12,
        choices=EntryType.choices,
        default=EntryType.MANUAL,
    )
    source_app = models.CharField(max_length=40, null=True, blank=True)
    source_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=EntryStatus.choices,
        default=EntryStatus.DRAFT,
    )
    reversal_of = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reversed_by",
    )
    total_debit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_credit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_journal_entries",
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="posted_journal_entries",
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounting_journal_entry"
        ordering = ["entry_date", "entry_number", "id"]
        indexes = [
            models.Index(fields=["entry_date", "entry_number"], name="ix_entry_date"),
            models.Index(fields=["source_app", "source_id"], name="ix_entry_source"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["period", "entry_number"],
                name="uq_accounting_entry_period_number",
            ),
            models.CheckConstraint(
                condition=Q(
                    entry_type__in=[
                        "OPENING",
                        "MANUAL",
                        "SALE",
                        "PURCHASE",
                        "PAYMENT",
                        "INVENTORY",
                        "ADJUSTMENT",
                        "CLOSING",
                        "REVERSAL",
                    ]
                ),
                name="ck_accounting_entry_type",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["DRAFT", "POSTED", "REVERSED"]),
                name="ck_accounting_entry_status",
            ),
            models.CheckConstraint(
                condition=Q(status="DRAFT")
                | (Q(entry_number__isnull=False) & Q(posted_at__isnull=False)),
                name="ck_accounting_entry_posted_meta",
            ),
            models.CheckConstraint(
                condition=Q(status="DRAFT")
                | (Q(total_debit=F("total_credit")) & Q(total_debit__gt=Decimal("0.00"))),
                name="ck_accounting_entry_balanced",
            ),
        ]

    def __str__(self) -> str:
        num = f"Part. N.º {self.entry_number}" if self.entry_number else f"Borrador #{self.pk}"
        return f"{num} ({self.entry_date}) - {self.description[:50]}"


class JournalEntryLine(models.Model):
    """Individual Debit/Credit line inside a JournalEntry (RN-01, RN-04)."""

    entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    line_no = models.SmallIntegerField()
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="journal_lines",
    )
    description = models.CharField(max_length=255, blank=True, default="")
    debit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    credit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        db_table = "accounting_journal_entry_line"
        ordering = ["line_no", "id"]
        indexes = [
            models.Index(fields=["account"], name="ix_line_account"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["entry", "line_no"],
                name="uq_accounting_entry_line_no",
            ),
            models.CheckConstraint(
                condition=Q(debit__gte=Decimal("0.00")) & Q(credit__gte=Decimal("0.00")),
                name="ck_accounting_line_non_negative",
            ),
            models.CheckConstraint(
                condition=(Q(debit__gt=Decimal("0.00")) & Q(credit=Decimal("0.00")))
                | (Q(credit__gt=Decimal("0.00")) & Q(debit=Decimal("0.00"))),
                name="ck_accounting_line_xor_debit_credit",
            ),
        ]

    def __str__(self) -> str:
        return f"#{self.line_no} {self.account.code} D:{self.debit} C:{self.credit}"


class PeriodBalance(models.Model):
    """Account balance snapshot per closed period (used by P3 ClosingService)."""

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="period_balances",
    )
    period = models.ForeignKey(
        "core.AccountingPeriod",
        on_delete=models.PROTECT,
        related_name="account_balances",
    )
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    debit_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    credit_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    closing_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        db_table = "accounting_period_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["account", "period"],
                name="uq_accounting_period_balance",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.account.code} @ {self.period.code}: {self.closing_balance}"
