from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F, Q


class PeriodStatus(models.TextChoices):
    OPEN = "OPEN", "Abierto"
    CLOSED = "CLOSED", "Cerrado"


class User(AbstractUser):
    """Custom user. Defined from day one so AUTH_USER_MODEL never has to change."""

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        ACCOUNTANT = "ACCOUNTANT", "Contador"
        AUDITOR = "AUDITOR", "Auditor"
        PURCHASING = "PURCHASING", "Compras y almacén"
        CASHIER = "CASHIER", "Caja / recepción"
        READONLY = "READONLY", "Solo lectura"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.READONLY)

    class Meta:
        db_table = "core_user"
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    role__in=[
                        "ADMIN",
                        "ACCOUNTANT",
                        "AUDITOR",
                        "PURCHASING",
                        "CASHIER",
                        "READONLY",
                    ]
                ),
                name="ck_core_user_role",
            ),
        ]

    @property
    def role_label(self) -> str:
        return self.get_role_display()

    @property
    def full_display_name(self) -> str:
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.username


class Company(models.Model):
    """Single-tenant company configuration (id = 1)."""

    id = models.SmallIntegerField(primary_key=True, default=1)
    legal_name = models.CharField(max_length=150)
    trade_name = models.CharField(max_length=150)
    nit = models.CharField(max_length=17)
    nrc = models.CharField(max_length=10)
    economic_activity = models.CharField(max_length=150, blank=True, default="")
    address = models.TextField(blank=True, default="")
    iva_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.1300"),
    )
    currency = models.CharField(max_length=3, default="USD")
    allow_negative_stock = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_company"
        verbose_name = "Empresa"
        verbose_name_plural = "Empresa"
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name="ck_core_company_singleton"),
            models.CheckConstraint(
                condition=Q(iva_rate__gte=Decimal("0"), iva_rate__lt=Decimal("1")),
                name="ck_core_company_iva_rate",
            ),
        ]

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> "Company":
        obj, _ = cls.objects.get_or_create(
            id=1,
            defaults={
                "legal_name": "Diamond Salón, S.A. de C.V.",
                "trade_name": "Diamond Salón Atelier",
                "nit": "0614-000000-000-0",
                "nrc": "000000-0",
                "economic_activity": "Peluquería y otros tratamientos de belleza",
                "iva_rate": Decimal("0.1300"),
                "currency": "USD",
                "allow_negative_stock": False,
            },
        )
        return obj

    def __str__(self) -> str:
        return self.trade_name


class Employee(models.Model):
    """Salon stylists, manicurists, and operational staff (not necessarily system users)."""

    class Position(models.TextChoices):
        STYLIST = "STYLIST", "Estilista"
        MANICURIST = "MANICURIST", "Manicurista"
        RECEPTION = "RECEPTION", "Recepción"
        OTHER = "OTHER", "Otro"

    full_name = models.CharField(max_length=150)
    position = models.CharField(max_length=20, choices=Position.choices, default=Position.STYLIST)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_employee"
        ordering = ["full_name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(position__in=["STYLIST", "MANICURIST", "RECEPTION", "OTHER"]),
                name="ck_core_employee_position",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_position_display()})"


class FiscalYear(models.Model):
    """Fiscal year container for monthly accounting periods."""

    year = models.SmallIntegerField(unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=PeriodStatus.choices,
        default=PeriodStatus.OPEN,
    )

    class Meta:
        db_table = "core_fiscal_year"
        ordering = ["-year"]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["OPEN", "CLOSED"]),
                name="ck_core_fiscal_year_status",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")),
                name="ck_core_fiscal_year_dates",
            ),
        ]

    def __str__(self) -> str:
        return f"Ejercicio {self.year} ({self.status})"


MONTH_NAMES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


class AccountingPeriod(models.Model):
    """Monthly accounting period (RF-CIE-01 .. RF-CIE-05)."""

    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.PROTECT,
        related_name="periods",
    )
    year = models.SmallIntegerField()
    month = models.SmallIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=PeriodStatus.choices,
        default=PeriodStatus.OPEN,
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Período de trabajo activo por defecto en la interfaz.",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="closed_periods",
    )

    class Meta:
        db_table = "core_accounting_period"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["year", "month"],
                name="uq_core_period_year_month",
            ),
            models.CheckConstraint(
                condition=Q(month__gte=1, month__lte=12),
                name="ck_core_period_month_range",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["OPEN", "CLOSED"]),
                name="ck_core_period_status",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="ck_core_period_dates",
            ),
            models.CheckConstraint(
                condition=Q(status="OPEN") | Q(closed_at__isnull=False),
                name="ck_core_period_closed_at",
            ),
        ]

    @property
    def month_name(self) -> str:
        return MONTH_NAMES_ES.get(self.month, str(self.month))

    @property
    def label(self) -> str:
        return f"{self.month_name} {self.year}"

    @property
    def code(self) -> str:
        return f"{self.month:02d}/{self.year}"

    def __str__(self) -> str:
        return f"{self.label} [{self.status}]"


class AuditLog(models.Model):
    """Append-only audit trail for every mutation and critical event (RF-SEG-03, RNF-05)."""

    class Action(models.TextChoices):
        CREATE = "CREATE", "Creación"
        UPDATE = "UPDATE", "Actualización"
        DELETE = "DELETE", "Eliminación"
        POST = "POST", "Mayorización / Contabilización"
        REVERSE = "REVERSE", "Reversión"
        VOID = "VOID", "Anulación"
        CLOSE = "CLOSE", "Cierre de período"
        REOPEN = "REOPEN", "Reapertura de período"
        LOGIN = "LOGIN", "Inicio de sesión"
        EXPORT = "EXPORT", "Exportación de reporte"

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    table_name = models.CharField(max_length=80)
    record_id = models.BigIntegerField(null=True, blank=True)
    before_data = models.JSONField(null=True, blank=True)
    after_data = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_audit_log"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["table_name", "record_id"], name="ix_audit_table_record"),
            models.Index(fields=["created_at"], name="ix_audit_created"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    action__in=[
                        "CREATE",
                        "UPDATE",
                        "DELETE",
                        "POST",
                        "REVERSE",
                        "VOID",
                        "CLOSE",
                        "REOPEN",
                        "LOGIN",
                        "EXPORT",
                    ]
                ),
                name="ck_core_audit_action",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.created_at}] {self.action} {self.table_name}#{self.record_id}"
