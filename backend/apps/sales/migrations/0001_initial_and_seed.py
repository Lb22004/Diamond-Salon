from datetime import date
from decimal import Decimal
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_sales_data(apps, schema_editor):
    Customer = apps.get_model("sales", "Customer")
    DocumentSeries = apps.get_model("sales", "DocumentSeries")
    Service = apps.get_model("sales", "Service")
    Sale = apps.get_model("sales", "Sale")
    SaleLine = apps.get_model("sales", "SaleLine")
    Account = apps.get_model("accounting", "Account")
    JournalEntry = apps.get_model("accounting", "JournalEntry")
    AccountingPeriod = apps.get_model("core", "AccountingPeriod")
    Employee = apps.get_model("core", "Employee")
    User = apps.get_model("core", "User")

    # 1. Customers
    cf_customer, _ = Customer.objects.update_or_create(
        name="Consumidor final",
        defaults={
            "customer_type": "FINAL_CONSUMER",
            "is_generic": True,
            "is_active": True,
        },
    )
    ana_customer, _ = Customer.objects.update_or_create(
        name="Ana Mejía",
        defaults={
            "customer_type": "FINAL_CONSUMER",
            "is_generic": False,
            "is_active": True,
        },
    )
    rosa_customer, _ = Customer.objects.update_or_create(
        name="Rosa Flores",
        defaults={
            "customer_type": "FINAL_CONSUMER",
            "is_generic": False,
            "is_active": True,
        },
    )
    Customer.objects.update_or_create(
        document_type="NIT",
        document_number="0614-200819-102-4",
        defaults={
            "name": "Eventos Glamour, S.A. de C.V.",
            "customer_type": "TAXPAYER",
            "nrc": "284910-5",
            "economic_activity": "Producción de eventos, bodas y pasarelas",
            "is_large_taxpayer": False,
            "email": "contabilidad@eventosglamour.sv",
            "phone": "2264-8890",
            "address": "Col. Escalón, San Salvador",
            "is_generic": False,
            "is_active": True,
        },
    )
    Customer.objects.update_or_create(
        document_type="NIT",
        document_number="0614-110210-101-1",
        defaults={
            "name": "Corporación Hotelera Real, S.A. de C.V.",
            "customer_type": "TAXPAYER",
            "nrc": "190422-8",
            "economic_activity": "Hotelería, turismo y centro de convenciones",
            "is_large_taxpayer": True,
            "email": "fiscales@hotelreal.com.sv",
            "phone": "2211-3300",
            "address": "Blvd. Los Próceres, San Salvador",
            "is_generic": False,
            "is_active": True,
        },
    )

    # 2. Authorized Document Series
    series_fcf, _ = DocumentSeries.objects.update_or_create(
        doc_type="FCF",
        is_active=True,
        defaults={
            "prefix": "FCF-",
            "resolution": "RES-DGII-2026-00142",
            "authorized_from": 1,
            "authorized_to": 9999,
            "next_number": 16,
            "valid_from": date(2026, 1, 1),
        },
    )
    DocumentSeries.objects.update_or_create(
        doc_type="CCF",
        is_active=True,
        defaults={
            "prefix": "CCF-",
            "resolution": "RES-DGII-2026-00143",
            "authorized_from": 1,
            "authorized_to": 9999,
            "next_number": 1,
            "valid_from": date(2026, 1, 1),
        },
    )
    DocumentSeries.objects.update_or_create(
        doc_type="NC",
        is_active=True,
        defaults={
            "prefix": "NC-",
            "resolution": "RES-DGII-2026-00144",
            "authorized_from": 1,
            "authorized_to": 999,
            "next_number": 1,
            "valid_from": date(2026, 1, 1),
        },
    )
    DocumentSeries.objects.update_or_create(
        doc_type="ND",
        is_active=True,
        defaults={
            "prefix": "ND-",
            "resolution": "RES-DGII-2026-00145",
            "authorized_from": 1,
            "authorized_to": 999,
            "next_number": 1,
            "valid_from": date(2026, 1, 1),
        },
    )

    # 3. Beauty Services Catalog
    acc_5101 = Account.objects.filter(code="5101").first()
    if not acc_5101:
        return

    services_seed = [
        ("SRV-001", "Servicio: corte y peinado", "STYLING", Decimal("25.00")),
        ("SRV-002", "Servicio: manicura + esmaltado", "NAILS", Decimal("15.00")),
        ("SRV-003", "Balayage & Colorimetría Couture", "COLOR", Decimal("85.00")),
        ("SRV-004", "Ritual Keratina & Hidratación Profunda", "TREATMENT", Decimal("45.00")),
        ("SRV-005", "Peinado de Gala & Maquillaje Editorial", "STYLING", Decimal("60.00")),
    ]
    srv_map = {}
    for code, name, cat, price in services_seed:
        srv, _ = Service.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "category": cat,
                "price": price,
                "income_account": acc_5101,
                "is_active": True,
            },
        )
        srv_map[code] = srv

    # 4. Seeded November 2026 Sales matching Vista 3 Mock-up (FCF-0012 to FCF-0015)
    nov_period = AccountingPeriod.objects.filter(year=2026, month=11).first()
    creator = User.objects.filter(username="contador").first() or User.objects.order_by("id").first()
    stylist = Employee.objects.order_by("id").first()
    if not nov_period or not creator:
        return

    entry_4 = JournalEntry.objects.filter(period=nov_period, entry_number=4).first()
    entry_5 = JournalEntry.objects.filter(period=nov_period, entry_number=5).first()

    sale_1, created_1 = Sale.objects.update_or_create(
        doc_type="FCF",
        doc_number="FCF-0012",
        defaults={
            "series": series_fcf,
            "sale_date": date(2026, 11, 2),
            "period": nov_period,
            "customer": ana_customer,
            "employee": stylist,
            "payment_method": "CASH",
            "taxable_amount": Decimal("22.12"),
            "exempt_amount": Decimal("0.00"),
            "non_subject_amount": Decimal("0.00"),
            "iva_amount": Decimal("2.88"),
            "iva_withheld": Decimal("0.00"),
            "total": Decimal("25.00"),
            "status": "ISSUED",
            "journal_entry": entry_4,
            "notes": "Servicio: corte y peinado",
            "created_by": creator,
        },
    )
    if created_1:
        SaleLine.objects.create(
            sale=sale_1,
            line_no=1,
            line_type="SERVICE",
            service=srv_map["SRV-001"],
            product_id=None,
            description="Servicio: corte y peinado",
            quantity=Decimal("1.000"),
            unit_price=Decimal("25.00"),
            discount=Decimal("0.00"),
            taxable_amount=Decimal("22.12"),
            iva_amount=Decimal("2.88"),
            total=Decimal("25.00"),
            unit_cost=None,
        )

    sale_2, created_2 = Sale.objects.update_or_create(
        doc_type="FCF",
        doc_number="FCF-0013",
        defaults={
            "series": series_fcf,
            "sale_date": date(2026, 11, 3),
            "period": nov_period,
            "customer": cf_customer,
            "employee": stylist,
            "payment_method": "CASH",
            "taxable_amount": Decimal("10.62"),
            "exempt_amount": Decimal("0.00"),
            "non_subject_amount": Decimal("0.00"),
            "iva_amount": Decimal("1.38"),
            "iva_withheld": Decimal("0.00"),
            "total": Decimal("12.00"),
            "status": "ISSUED",
            "journal_entry": entry_5,
            "notes": "Venta: champú nutritivo",
            "created_by": creator,
        },
    )
    if created_2:
        SaleLine.objects.create(
            sale=sale_2,
            line_no=1,
            line_type="PRODUCT",
            service=None,
            product_id=1,
            description="Venta: champú nutritivo",
            quantity=Decimal("1.000"),
            unit_price=Decimal("12.00"),
            discount=Decimal("0.00"),
            taxable_amount=Decimal("10.62"),
            iva_amount=Decimal("1.38"),
            total=Decimal("12.00"),
            unit_cost=Decimal("7.0000"),
        )

    sale_3, created_3 = Sale.objects.update_or_create(
        doc_type="FCF",
        doc_number="FCF-0014",
        defaults={
            "series": series_fcf,
            "sale_date": date(2026, 11, 4),
            "period": nov_period,
            "customer": rosa_customer,
            "employee": stylist,
            "payment_method": "CASH",
            "taxable_amount": Decimal("13.27"),
            "exempt_amount": Decimal("0.00"),
            "non_subject_amount": Decimal("0.00"),
            "iva_amount": Decimal("1.73"),
            "iva_withheld": Decimal("0.00"),
            "total": Decimal("15.00"),
            "status": "ISSUED",
            "journal_entry": entry_4,
            "notes": "Servicio: manicura + esmaltado",
            "created_by": creator,
        },
    )
    if created_3:
        SaleLine.objects.create(
            sale=sale_3,
            line_no=1,
            line_type="SERVICE",
            service=srv_map["SRV-002"],
            product_id=None,
            description="Servicio: manicura + esmaltado",
            quantity=Decimal("1.000"),
            unit_price=Decimal("15.00"),
            discount=Decimal("0.00"),
            taxable_amount=Decimal("13.27"),
            iva_amount=Decimal("1.73"),
            total=Decimal("15.00"),
            unit_cost=None,
        )

    sale_4, created_4 = Sale.objects.update_or_create(
        doc_type="FCF",
        doc_number="FCF-0015",
        defaults={
            "series": series_fcf,
            "sale_date": date(2026, 11, 5),
            "period": nov_period,
            "customer": cf_customer,
            "employee": stylist,
            "payment_method": "CASH",
            "taxable_amount": Decimal("15.93"),
            "exempt_amount": Decimal("0.00"),
            "non_subject_amount": Decimal("0.00"),
            "iva_amount": Decimal("2.07"),
            "iva_withheld": Decimal("0.00"),
            "total": Decimal("18.00"),
            "status": "ISSUED",
            "journal_entry": entry_5,
            "notes": "Venta: serum de brillo",
            "created_by": creator,
        },
    )
    if created_4:
        SaleLine.objects.create(
            sale=sale_4,
            line_no=1,
            line_type="PRODUCT",
            service=None,
            product_id=3,
            description="Venta: serum de brillo",
            quantity=Decimal("1.000"),
            unit_price=Decimal("18.00"),
            discount=Decimal("0.00"),
            taxable_amount=Decimal("15.93"),
            iva_amount=Decimal("2.07"),
            total=Decimal("18.00"),
            unit_cost=Decimal("10.5000"),
        )


def unseed_sales_data(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounting", "0001_initial_and_seed"),
        ("core", "0002_core_domain_and_seed"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("customer_type", models.CharField(choices=[("FINAL_CONSUMER", "Consumidor Final"), ("TAXPAYER", "Contribuyente IVA")], default="FINAL_CONSUMER", max_length=15)),
                ("document_type", models.CharField(blank=True, choices=[("DUI", "DUI"), ("NIT", "NIT"), ("PASSPORT", "Pasaporte"), ("OTHER", "Otro")], max_length=10, null=True)),
                ("document_number", models.CharField(blank=True, max_length=20, null=True)),
                ("nrc", models.CharField(blank=True, max_length=10, null=True)),
                ("economic_activity", models.CharField(blank=True, max_length=150, null=True)),
                ("is_large_taxpayer", models.BooleanField(default=False)),
                ("email", models.EmailField(blank=True, max_length=254, null=True)),
                ("phone", models.CharField(blank=True, max_length=30, null=True)),
                ("address", models.TextField(blank=True, null=True)),
                ("is_generic", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "sales_customer",
                "ordering": ["-is_generic", "name"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("customer_type", "TAXPAYER"), _negated=True),
                            models.Q(
                                ("nrc__isnull", False),
                                models.Q(("nrc", ""), _negated=True),
                                ("document_number__isnull", False),
                                models.Q(("document_number", ""), _negated=True),
                            ),
                            _connector="OR",
                        ),
                        name="ck_sales_customer_taxpayer_ids",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("document_number__isnull", False), models.Q(("document_number", ""), _negated=True)),
                        fields=("document_type", "document_number"),
                        name="ux_customer_document",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="DocumentSeries",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("doc_type", models.CharField(choices=[("FCF", "Factura Consumidor Final (FCF)"), ("CCF", "Comprobante de Crédito Fiscal (CCF)"), ("NC", "Nota de Crédito (NC)"), ("ND", "Nota de Débito (ND)")], max_length=3)),
                ("prefix", models.CharField(max_length=10)),
                ("resolution", models.CharField(blank=True, max_length=60, null=True)),
                ("authorized_from", models.IntegerField(default=1)),
                ("authorized_to", models.IntegerField(default=9999)),
                ("next_number", models.IntegerField(default=1)),
                ("valid_from", models.DateField()),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "sales_document_series",
                "ordering": ["doc_type", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("authorized_from__gt", 0), ("authorized_to__gte", models.F("authorized_from"))),
                        name="ck_sales_series_range",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("is_active", True)),
                        fields=("doc_type",),
                        name="ux_series_active",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Sale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("doc_type", models.CharField(choices=[("FCF", "Factura Consumidor Final (FCF)"), ("CCF", "Comprobante de Crédito Fiscal (CCF)"), ("NC", "Nota de Crédito (NC)"), ("ND", "Nota de Débito (ND)")], max_length=3)),
                ("doc_number", models.CharField(max_length=20)),
                ("sale_date", models.DateField()),
                ("payment_method", models.CharField(choices=[("CASH", "Efectivo (Caja)"), ("CARD", "Tarjeta POS (Banco)"), ("TRANSFER", "Transferencia Bancaria"), ("CREDIT", "Crédito Cliente (CxC)")], default="CASH", max_length=10)),
                ("taxable_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("exempt_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("non_subject_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("iva_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("iva_withheld", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("status", models.CharField(choices=[("ISSUED", "Emitida"), ("VOIDED", "Anulada")], default="ISSUED", max_length=10)),
                ("void_reason", models.CharField(blank=True, max_length=255, null=True)),
                ("voided_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_sales", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sales", to="sales.customer")),
                ("employee", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sales", to="core.employee")),
                ("journal_entry", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sales_documents", to="accounting.journalentry")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sales", to="core.accountingperiod")),
                ("related_sale", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="adjustments", to="sales.sale")),
                ("series", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sales", to="sales.documentseries")),
            ],
            options={
                "db_table": "sales_sale",
                "ordering": ["-sale_date", "-id"],
            },
        ),
        migrations.CreateModel(
            name="Service",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(max_length=150)),
                ("category", models.CharField(choices=[("HAIRCUT", "Corte"), ("STYLING", "Peinado & Brushing"), ("COLOR", "Colorimetría"), ("TREATMENT", "Tratamiento Capilar"), ("NAILS", "Uñas & Spa"), ("OTHER", "Otro Servicio")], default="STYLING", max_length=20)),
                ("price", models.DecimalField(decimal_places=2, default=Decimal("0.00"), help_text="Precio de lista con IVA incluido (13%)", max_digits=12)),
                ("is_active", models.BooleanField(default=True)),
                ("income_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="services", to="accounting.account")),
            ],
            options={
                "db_table": "sales_service",
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="SaleLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("line_no", models.SmallIntegerField()),
                ("line_type", models.CharField(choices=[("SERVICE", "Servicio en Salón (Cabina)"), ("PRODUCT", "Producto Retail (Vitrina)")], max_length=10)),
                ("product_id", models.BigIntegerField(blank=True, db_column="product_id", null=True)),
                ("description", models.CharField(max_length=255)),
                ("quantity", models.DecimalField(decimal_places=3, default=Decimal("1.000"), max_digits=12)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("discount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("taxable_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("iva_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("total", models.DecimalField(decimal_places=2, max_digits=14)),
                ("unit_cost", models.DecimalField(blank=True, decimal_places=4, help_text="Costo promedio ponderado unitario al momento de la venta (solo VITRINA)", max_digits=14, null=True)),
                ("sale", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="sales.sale")),
                ("service", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sale_lines", to="sales.service")),
            ],
            options={
                "db_table": "sales_sale_line",
                "ordering": ["sale", "line_no"],
            },
        ),
        migrations.CreateModel(
            name="ServiceSupply",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_id", models.BigIntegerField(db_column="product_id")),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=12)),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="supplies", to="sales.service")),
            ],
            options={
                "db_table": "sales_service_supply",
            },
        ),
        migrations.AddIndex(
            model_name="sale",
            index=models.Index(fields=["sale_date"], name="ix_sale_date"),
        ),
        migrations.AddIndex(
            model_name="sale",
            index=models.Index(fields=["period", "doc_type"], name="ix_sale_period"),
        ),
        migrations.AddConstraint(
            model_name="sale",
            constraint=models.UniqueConstraint(fields=("doc_type", "doc_number"), name="ux_sales_doc_type_number"),
        ),
        migrations.AddConstraint(
            model_name="sale",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("taxable_amount__gte", 0),
                    ("exempt_amount__gte", 0),
                    ("non_subject_amount__gte", 0),
                    ("iva_amount__gte", 0),
                    ("iva_withheld__gte", 0),
                    ("total__gte", 0),
                ),
                name="ck_sales_sale_amounts_nonneg",
            ),
        ),
        migrations.AddConstraint(
            model_name="service",
            constraint=models.CheckConstraint(condition=models.Q(("price__gte", 0)), name="ck_sales_service_price_nonneg"),
        ),
        migrations.AddConstraint(
            model_name="saleline",
            constraint=models.UniqueConstraint(fields=("sale", "line_no"), name="ux_sales_sale_line_no"),
        ),
        migrations.AddConstraint(
            model_name="saleline",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("quantity__gt", 0),
                    ("unit_price__gte", 0),
                    ("discount__gte", 0),
                    ("taxable_amount__gte", 0),
                    ("iva_amount__gte", 0),
                    ("total__gte", 0),
                ),
                name="ck_sales_line_amounts_nonneg",
            ),
        ),
        migrations.AddConstraint(
            model_name="servicesupply",
            constraint=models.UniqueConstraint(fields=("service", "product_id"), name="ux_sales_service_supply_unique"),
        ),
        migrations.AddConstraint(
            model_name="servicesupply",
            constraint=models.CheckConstraint(condition=models.Q(("quantity__gt", 0)), name="ck_sales_service_supply_qty_pos"),
        ),
        migrations.RunPython(seed_sales_data, unseed_sales_data),
    ]
