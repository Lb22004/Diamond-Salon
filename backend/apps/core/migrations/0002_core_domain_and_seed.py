# Generated for Diamond Salón — P1 Core Domain Models & Seed Data
import calendar
from datetime import date
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations, models
from django.db.models import F, Q


def seed_core_data(apps, schema_editor):
    Company = apps.get_model("core", "Company")
    User = apps.get_model("core", "User")
    Employee = apps.get_model("core", "Employee")
    FiscalYear = apps.get_model("core", "FiscalYear")
    AccountingPeriod = apps.get_model("core", "AccountingPeriod")

    # 1. Single-tenant company (seed.sql)
    Company.objects.update_or_create(
        id=1,
        defaults={
            "legal_name": "Diamond Salón, S.A. de C.V.",
            "trade_name": "Diamond Salón Atelier",
            "nit": "0614-000000-000-0",
            "nrc": "000000-0",
            "economic_activity": "Peluquería y otros tratamientos de belleza",
            "address": "Colonia Escalón, San Salvador, El Salvador",
            "iva_rate": Decimal("0.1300"),
            "currency": "USD",
            "allow_negative_stock": False,
        },
    )

    # 2. System user (from seed.sql) + role users for team testing / demo
    User.objects.update_or_create(
        username="system",
        defaults={
            "password": "!",
            "first_name": "Sistema",
            "last_name": "Automático",
            "email": "system@diamondsalon.sv",
            "role": "ADMIN",
            "is_staff": False,
            "is_superuser": False,
            "is_active": True,
        },
    )

    demo_users = [
        ("admin", "Maira", "Administración", "admin@diamondsalon.sv", "ADMIN", True, True),
        ("contador", "Jose Roberto", "Contador General", "contador@diamondsalon.sv", "ACCOUNTANT", True, False),
        ("auditor", "Ferdinand", "Auditor Externo", "auditor@diamondsalon.sv", "AUDITOR", False, False),
        ("compras", "Víctor", "Flores", "compras@diamondsalon.sv", "PURCHASING", False, False),
        ("cajero", "Valeria", "Recepción", "caja@diamondsalon.sv", "CASHIER", False, False),
        ("lectura", "Gerencia", "Diamond", "gerencia@diamondsalon.sv", "READONLY", False, False),
    ]
    default_pw = make_password("diamond2026")
    for username, first_name, last_name, email, role, is_staff, is_superuser in demo_users:
        User.objects.update_or_create(
            username=username,
            defaults={
                "password": default_pw,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "role": role,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
                "is_active": True,
            },
        )

    # 3. Fiscal year 2026 & 12 monthly accounting periods (seed.sql)
    fy_2026, _ = FiscalYear.objects.update_or_create(
        year=2026,
        defaults={
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "status": "OPEN",
        },
    )

    for month in range(1, 13):
        last_day = calendar.monthrange(2026, month)[1]
        AccountingPeriod.objects.update_or_create(
            year=2026,
            month=month,
            defaults={
                "fiscal_year": fy_2026,
                "start_date": date(2026, month, 1),
                "end_date": date(2026, month, last_day),
                "status": "OPEN",
                "is_active": month == 11,  # November 2026 active period per SRS mock-ups
            },
        )

    # 4. Sample salon employees (referenced in SRS/DB_DESIGN)
    sample_employees = [
        ("Roberto G.", "STYLIST"),
        ("Andrea M.", "STYLIST"),
        ("Sofía L.", "MANICURIST"),
        ("Valeria R.", "RECEPTION"),
    ]
    for full_name, position in sample_employees:
        Employee.objects.get_or_create(
            full_name=full_name,
            defaults={"position": position, "is_active": True},
        )


def unseed_core_data(apps, schema_editor):
    # Safe no-op on reverse to avoid destructive cascade issues if referenced
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.SmallIntegerField(default=1, primary_key=True, serialize=False)),
                ("legal_name", models.CharField(max_length=150)),
                ("trade_name", models.CharField(max_length=150)),
                ("nit", models.CharField(max_length=17)),
                ("nrc", models.CharField(max_length=10)),
                ("economic_activity", models.CharField(blank=True, default="", max_length=150)),
                ("address", models.TextField(blank=True, default="")),
                ("iva_rate", models.DecimalField(decimal_places=4, default=Decimal("0.1300"), max_digits=5)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("allow_negative_stock", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Empresa",
                "verbose_name_plural": "Empresa",
                "db_table": "core_company",
            },
        ),
        migrations.CreateModel(
            name="Employee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=150)),
                (
                    "position",
                    models.CharField(
                        choices=[
                            ("STYLIST", "Estilista"),
                            ("MANICURIST", "Manicurista"),
                            ("RECEPTION", "Recepción"),
                            ("OTHER", "Otro"),
                        ],
                        default="STYLIST",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "core_employee",
                "ordering": ["full_name"],
            },
        ),
        migrations.CreateModel(
            name="FiscalYear",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.SmallIntegerField(unique=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[("OPEN", "Abierto"), ("CLOSED", "Cerrado")],
                        default="OPEN",
                        max_length=10,
                    ),
                ),
            ],
            options={
                "db_table": "core_fiscal_year",
                "ordering": ["-year"],
            },
        ),
        migrations.CreateModel(
            name="AccountingPeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.SmallIntegerField()),
                ("month", models.SmallIntegerField()),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[("OPEN", "Abierto"), ("CLOSED", "Cerrado")],
                        default="OPEN",
                        max_length=10,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=False,
                        help_text="Período de trabajo activo por defecto en la interfaz.",
                    ),
                ),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "closed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="closed_periods",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "fiscal_year",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="periods",
                        to="core.fiscalyear",
                    ),
                ),
            ],
            options={
                "db_table": "core_accounting_period",
                "ordering": ["-year", "-month"],
            },
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("CREATE", "Creación"),
                            ("UPDATE", "Actualización"),
                            ("DELETE", "Eliminación"),
                            ("POST", "Mayorización / Contabilización"),
                            ("REVERSE", "Reversión"),
                            ("VOID", "Anulación"),
                            ("CLOSE", "Cierre de período"),
                            ("REOPEN", "Reapertura de período"),
                            ("LOGIN", "Inicio de sesión"),
                            ("EXPORT", "Exportación de reporte"),
                        ],
                        max_length=20,
                    ),
                ),
                ("table_name", models.CharField(max_length=80)),
                ("record_id", models.BigIntegerField(blank=True, null=True)),
                ("before_data", models.JSONField(blank=True, null=True)),
                ("after_data", models.JSONField(blank=True, null=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "core_audit_log",
                "ordering": ["-created_at", "-id"],
            },
        ),
        # Constraints & Indexes
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
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
        ),
        migrations.AddConstraint(
            model_name="company",
            constraint=models.CheckConstraint(
                condition=Q(id=1),
                name="ck_core_company_singleton",
            ),
        ),
        migrations.AddConstraint(
            model_name="company",
            constraint=models.CheckConstraint(
                condition=Q(iva_rate__gte=Decimal("0"), iva_rate__lt=Decimal("1")),
                name="ck_core_company_iva_rate",
            ),
        ),
        migrations.AddConstraint(
            model_name="employee",
            constraint=models.CheckConstraint(
                condition=Q(position__in=["STYLIST", "MANICURIST", "RECEPTION", "OTHER"]),
                name="ck_core_employee_position",
            ),
        ),
        migrations.AddConstraint(
            model_name="fiscalyear",
            constraint=models.CheckConstraint(
                condition=Q(status__in=["OPEN", "CLOSED"]),
                name="ck_core_fiscal_year_status",
            ),
        ),
        migrations.AddConstraint(
            model_name="fiscalyear",
            constraint=models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")),
                name="ck_core_fiscal_year_dates",
            ),
        ),
        migrations.AddConstraint(
            model_name="accountingperiod",
            constraint=models.UniqueConstraint(
                fields=("year", "month"),
                name="uq_core_period_year_month",
            ),
        ),
        migrations.AddConstraint(
            model_name="accountingperiod",
            constraint=models.CheckConstraint(
                condition=Q(month__gte=1, month__lte=12),
                name="ck_core_period_month_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="accountingperiod",
            constraint=models.CheckConstraint(
                condition=Q(status__in=["OPEN", "CLOSED"]),
                name="ck_core_period_status",
            ),
        ),
        migrations.AddConstraint(
            model_name="accountingperiod",
            constraint=models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="ck_core_period_dates",
            ),
        ),
        migrations.AddConstraint(
            model_name="accountingperiod",
            constraint=models.CheckConstraint(
                condition=Q(status="OPEN") | Q(closed_at__isnull=False),
                name="ck_core_period_closed_at",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["table_name", "record_id"], name="ix_audit_table_record"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["created_at"], name="ix_audit_created"),
        ),
        migrations.AddConstraint(
            model_name="auditlog",
            constraint=models.CheckConstraint(
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
        ),
        migrations.RunPython(seed_core_data, unseed_core_data),
    ]
