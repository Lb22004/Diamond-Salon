from datetime import date
from decimal import Decimal

from django.db import migrations


PG_APPEND_ONLY_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION fn_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_inventory_movement_append_only ON inventory_movement;
CREATE TRIGGER trg_inventory_movement_append_only
    BEFORE UPDATE OR DELETE ON inventory_movement
    FOR EACH ROW EXECUTE FUNCTION fn_append_only();
"""

PURCHASE_BOOK_VIEW_SQL = """
CREATE VIEW purchases_v_purchase_book AS
SELECT
    p.id AS purchase_id,
    p.doc_date,
    p.period_id,
    p.doc_type,
    p.doc_number,
    sp.name AS supplier_name,
    sp.brands_description AS supplier_brands,
    sp.nrc AS supplier_nrc,
    sp.nit AS supplier_nit,
    p.destination,
    p.taxable_amount,
    p.exempt_amount,
    p.iva_credit,
    p.iva_perceived,
    p.total,
    p.amount_paid,
    p.payment_status,
    p.status,
    p.journal_entry_id
FROM purchases_purchase p
JOIN purchases_supplier sp ON sp.id = p.supplier_id;
"""


def install_triggers_and_views(apps, schema_editor):
    schema_editor.execute("DROP VIEW IF EXISTS purchases_v_purchase_book;", params=None)
    schema_editor.execute(PURCHASE_BOOK_VIEW_SQL, params=None)
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(PG_APPEND_ONLY_TRIGGER_SQL, params=None)


def remove_triggers_and_views(apps, schema_editor):
    schema_editor.execute("DROP VIEW IF EXISTS purchases_v_purchase_book;", params=None)
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            "DROP TRIGGER IF EXISTS trg_inventory_movement_append_only ON inventory_movement;",
            params=None,
        )


def seed_inventory_and_purchases(apps, schema_editor):
    Account = apps.get_model("accounting", "Account")
    JournalEntry = apps.get_model("accounting", "JournalEntry")
    AccountingPeriod = apps.get_model("core", "AccountingPeriod")
    User = apps.get_model("core", "User")
    Employee = apps.get_model("core", "Employee")
    Service = apps.get_model("sales", "Service")
    ServiceSupply = apps.get_model("sales", "ServiceSupply")

    Category = apps.get_model("inventory", "Category")
    Location = apps.get_model("inventory", "Location")
    Product = apps.get_model("inventory", "Product")
    Stock = apps.get_model("inventory", "Stock")
    Consumption = apps.get_model("inventory", "Consumption")
    InventoryMovement = apps.get_model("inventory", "InventoryMovement")

    Supplier = apps.get_model("purchases", "Supplier")
    Purchase = apps.get_model("purchases", "Purchase")
    PurchaseLine = apps.get_model("purchases", "PurchaseLine")
    SupplierPayment = apps.get_model("purchases", "SupplierPayment")

    acc_vitrina = Account.objects.filter(code="110501").first()
    acc_cabina = Account.objects.filter(code="110502").first()
    acc_caja = Account.objects.filter(code="110101").first()
    nov_period = AccountingPeriod.objects.filter(year=2026, month=11).first()
    creator = User.objects.filter(username="contador").first() or User.objects.order_by("id").first()
    stylist = Employee.objects.order_by("id").first()

    if not acc_vitrina or not acc_cabina or not nov_period or not creator:
        return

    # 1. Locations (seed.sql)
    locations_data = [
        ("VIT", "Vitrina", "VITRINA"),
        ("CAB1", "Cabina 1", "CABINA"),
        ("CAB2", "Cabina 2", "CABINA"),
        ("GEN", "General", "WAREHOUSE"),
    ]
    loc_map = {}
    for code, name, ltype in locations_data:
        loc, _ = Location.objects.update_or_create(
            code=code,
            defaults={"name": name, "location_type": ltype, "is_active": True},
        )
        loc_map[code] = loc

    # 2. Categories
    cat_hair_vit, _ = Category.objects.get_or_create(
        name="Cuidado Capilar Retail", inventory_type="VITRINA"
    )
    cat_nails_vit, _ = Category.objects.get_or_create(
        name="Cosmética & Esmaltes", inventory_type="VITRINA"
    )
    cat_color_cab, _ = Category.objects.get_or_create(
        name="Colorimetría & Químicos", inventory_type="CABINA"
    )
    cat_supply_cab, _ = Category.objects.get_or_create(
        name="Insumos Descartables & Solventes", inventory_type="CABINA"
    )

    # 3. Suppliers (Vista 4 Mock-up: 3 active suppliers)
    sup_bella, _ = Supplier.objects.update_or_create(
        nit="0614-120415-102-8",
        defaults={
            "name": "Distribuidora Bella",
            "trade_name": "Distribuidora Cosmética S.A. de C.V.",
            "nrc": "240812-4",
            "taxpayer_category": "LARGE",
            "brands_description": "L'Oréal, Kérastase",
            "contact_name": "Claudia Solís",
            "phone": "2264-8800",
            "email": "facturacion@distribuidorabella.com.sv",
            "address": "Zona Industrial Santa Elena, Antiguo Cuscatlán",
            "is_active": True,
        },
    )
    sup_insumos, _ = Supplier.objects.update_or_create(
        nit="0614-190818-105-1",
        defaults={
            "name": "Insumos Pro",
            "trade_name": "Insumos Pro S.A. de C.V.",
            "nrc": "261904-8",
            "taxpayer_category": "MEDIUM",
            "brands_description": "Químicos & Decolorantes",
            "contact_name": "Héctor Méndez",
            "phone": "2243-5190",
            "email": "ventas@insumospro.com.sv",
            "address": "Colonia Escalón, San Salvador",
            "is_active": True,
        },
    )
    sup_color, _ = Supplier.objects.update_or_create(
        nit="0614-251120-109-3",
        defaults={
            "name": "Color & Style",
            "trade_name": "Color & Style Atelier S.A. de C.V.",
            "nrc": "289103-1",
            "taxpayer_category": "MEDIUM",
            "brands_description": "Tintes Orgánicos",
            "contact_name": "Valeria Rivas",
            "phone": "2298-3412",
            "email": "pedidos@colorandstyle.com.sv",
            "address": "Boulevard del Hipódromo, San Benito",
            "is_active": True,
        },
    )

    # 4. Products (Vista 2 Mock-up: 4 Vitrina = 61 u @ $889.50 cost; 4 Cabina = 48 u/L @ $551.50 cost)
    # Reconciles 100% with Ledger 110501 ($889.50) and 110502 ($551.50)!
    products_spec = [
        # VITRINA (110501)
        {
            "sku": "VIT-001",
            "barcode": "750100110001",
            "name": "Champú nutritivo 300ml",
            "brand": "L'Oréal Professionnel Serie Expert",
            "presentation": "300ml",
            "category": cat_hair_vit,
            "inventory_type": "VITRINA",
            "unit_of_measure": "UNIT",
            "account": acc_vitrina,
            "sale_price": Decimal("12.00"),
            "average_cost": Decimal("7.0000"),
            "min_stock": Decimal("5.000"),
            "default_supplier": sup_bella,
            "location": loc_map["VIT"],
            "qty": Decimal("18.000"),
        },
        {
            "sku": "VIT-002",
            "barcode": "750100110002",
            "name": "Mascarilla reconstructiva",
            "brand": "Kérastase Resistance 250ml",
            "presentation": "250ml",
            "category": cat_hair_vit,
            "inventory_type": "VITRINA",
            "unit_of_measure": "UNIT",
            "account": acc_vitrina,
            "sale_price": Decimal("22.00"),
            "average_cost": Decimal("24.0000"),
            "min_stock": Decimal("5.000"),
            "default_supplier": sup_bella,
            "location": loc_map["VIT"],
            "qty": Decimal("11.000"),
        },
        {
            "sku": "VIT-003",
            "barcode": "750100110003",
            "name": "Serum de brillo",
            "brand": "Moroccanoil Treatment 100ml",
            "presentation": "100ml",
            "category": cat_hair_vit,
            "inventory_type": "VITRINA",
            "unit_of_measure": "UNIT",
            "account": acc_vitrina,
            "sale_price": Decimal("18.00"),
            "average_cost": Decimal("10.5000"),
            "min_stock": Decimal("10.000"),  # Critical stock: 7 <= 10
            "default_supplier": sup_bella,
            "location": loc_map["VIT"],
            "qty": Decimal("7.000"),
        },
        {
            "sku": "VIT-004",
            "barcode": "750100110004",
            "name": "Esmalte profesional",
            "brand": "OPI Nail Lacquer Palette Atelier",
            "presentation": "15ml",
            "category": cat_nails_vit,
            "inventory_type": "VITRINA",
            "unit_of_measure": "UNIT",
            "account": acc_vitrina,
            "sale_price": Decimal("6.50"),
            "average_cost": Decimal("17.0400"),
            "min_stock": Decimal("10.000"),
            "default_supplier": sup_bella,
            "location": loc_map["VIT"],
            "qty": Decimal("25.000"),
        },
        # CABINA (110502)
        {
            "sku": "CAB-001",
            "barcode": "750200220001",
            "name": "Tinte / colorante",
            "brand": "Majirel Tubos 50ml (Gama Castaños)",
            "presentation": "Tubos 50ml",
            "category": cat_color_cab,
            "inventory_type": "CABINA",
            "unit_of_measure": "UNIT",
            "account": acc_cabina,
            "sale_price": None,
            "average_cost": Decimal("15.0000"),
            "min_stock": Decimal("5.000"),
            "default_supplier": sup_color,
            "location": loc_map["CAB1"],
            "qty": Decimal("9.000"),
        },
        {
            "sku": "CAB-002",
            "barcode": "750200220002",
            "name": "Acondicionador sellador",
            "brand": "PH Acidifying Rinse Garrafa 1000ml",
            "presentation": "Garrafa 1000ml",
            "category": cat_color_cab,
            "inventory_type": "CABINA",
            "unit_of_measure": "UNIT",
            "account": acc_cabina,
            "sale_price": None,
            "average_cost": Decimal("25.3000"),
            "min_stock": Decimal("8.000"),  # Critical stock: 5 <= 8
            "default_supplier": sup_insumos,
            "location": loc_map["CAB2"],
            "qty": Decimal("5.000"),
        },
        {
            "sku": "CAB-003",
            "barcode": "750200220003",
            "name": "Acetona pura",
            "brand": "Solvente grado técnico para remoción",
            "presentation": "Galón 1L",
            "category": cat_supply_cab,
            "inventory_type": "CABINA",
            "unit_of_measure": "LITER",
            "account": acc_cabina,
            "sale_price": None,
            "average_cost": Decimal("12.5000"),
            "min_stock": Decimal("2.000"),
            "default_supplier": sup_insumos,
            "location": loc_map["GEN"],
            "qty": Decimal("4.000"),
        },
        {
            "sku": "CAB-004",
            "barcode": "750200220004",
            "name": "Algodón / insumos",
            "brand": "Paquetes desmaquillantes prensados",
            "presentation": "Paquete 500u",
            "category": cat_supply_cab,
            "inventory_type": "CABINA",
            "unit_of_measure": "UNIT",
            "account": acc_cabina,
            "sale_price": None,
            "average_cost": Decimal("8.0000"),
            "min_stock": Decimal("10.000"),
            "default_supplier": sup_insumos,
            "location": loc_map["GEN"],
            "qty": Decimal("30.000"),
        },
    ]

    entry_1 = JournalEntry.objects.filter(period=nov_period, entry_number=1).first()
    entry_2 = JournalEntry.objects.filter(period=nov_period, entry_number=2).first()
    entry_3 = JournalEntry.objects.filter(period=nov_period, entry_number=3).first()
    entry_6 = JournalEntry.objects.filter(period=nov_period, entry_number=6).first()
    entry_7 = JournalEntry.objects.filter(period=nov_period, entry_number=7).first()

    prod_map = {}
    for spec in products_spec:
        loc = spec.pop("location")
        qty = spec.pop("qty")
        sku = spec["sku"]
        prod, _ = Product.objects.update_or_create(sku=sku, defaults=spec)
        prod_map[sku] = prod

        Stock.objects.update_or_create(
            product=prod,
            location=loc,
            defaults={"quantity": qty},
        )

        if not InventoryMovement.objects.filter(product=prod).exists():
            tot_cost = (qty * prod.average_cost).quantize(Decimal("0.01"))
            InventoryMovement.objects.create(
                product=prod,
                location=loc,
                movement_date=date(2026, 11, 1),
                movement_type="OPENING",
                direction=1,
                quantity=qty,
                unit_cost=prod.average_cost,
                total_cost=tot_cost,
                balance_quantity=qty,
                balance_avg_cost=prod.average_cost,
                source_app="inventory.seed",
                source_id=prod.id,
                journal_entry=entry_1,
                notes=f"Inventario físico certificado en {loc.name}",
                created_by=creator,
            )

    # Seed ServiceSupply recipes (RF-INV-10)
    srv_color = Service.objects.filter(code="SRV-003").first()
    if srv_color and "CAB-001" in prod_map:
        ServiceSupply.objects.get_or_create(
            service=srv_color,
            product_id=prod_map["CAB-001"].id,
            defaults={"quantity": Decimal("1.000")},
        )

    # Seed Cabina Consumption header linked to Entry #6
    if entry_6 and not Consumption.objects.filter(journal_entry=entry_6).exists():
        Consumption.objects.create(
            consumption_date=date(2026, 11, 7),
            location=loc_map["CAB1"],
            employee=stylist,
            sale_id=None,
            notes="Consumo diario de tinte y oxidante en servicios de Cabina 1",
            journal_entry=entry_6,
            created_by=creator,
        )

    # 5. Seed 3 November 2026 Purchases matching Vista 4 Mock-up:
    #    - 01/11/26 CCF-4521 Distribuidora Bella (Vitrina): $150.00 + $19.50 = $169.50
    #    - 01/11/26 CCF-4522 Insumos Pro (Cabina): $90.00 + $11.70 = $101.70 (PAID via Entry #7)
    #    - 03/11/26 CCF-4530 Color & Style (Cabina): $60.00 + $7.80 = $67.80
    #    Totals: Base Gravada = $300.00, IVA Crédito = $39.00, Total Compras = $339.00
    #    Distribution: Vitrina = $169.50 (50%), Cabina = $169.50 (50%)
    p1, created_p1 = Purchase.objects.update_or_create(
        supplier=sup_bella,
        doc_type="CCF",
        doc_number="CCF-4521",
        defaults={
            "doc_date": date(2026, 11, 1),
            "period": nov_period,
            "destination": "VITRINA",
            "taxable_amount": Decimal("150.00"),
            "exempt_amount": Decimal("0.00"),
            "iva_credit": Decimal("19.50"),
            "iva_perceived": Decimal("0.00"),
            "total": Decimal("169.50"),
            "payment_condition": "CREDIT",
            "due_date": date(2026, 11, 30),
            "amount_paid": Decimal("0.00"),
            "payment_status": "PENDING",
            "status": "REGISTERED",
            "journal_entry": entry_2,
            "notes": "Lote ingresado con código de barras de venta directa (L'Oréal, Kérastase).",
            "created_by": creator,
        },
    )
    if created_p1:
        PurchaseLine.objects.create(
            purchase=p1,
            line_no=1,
            product=prod_map["VIT-001"],
            location=loc_map["VIT"],
            description="Lote Champú nutritivo 300ml y Mascarilla Kérastase para Vitrina",
            quantity=Decimal("15.000"),
            unit_cost=Decimal("10.0000"),
            taxable_amount=Decimal("150.00"),
            iva_amount=Decimal("19.50"),
        )

    p2, created_p2 = Purchase.objects.update_or_create(
        supplier=sup_insumos,
        doc_type="CCF",
        doc_number="CCF-4522",
        defaults={
            "doc_date": date(2026, 11, 1),
            "period": nov_period,
            "destination": "CABINA",
            "taxable_amount": Decimal("90.00"),
            "exempt_amount": Decimal("0.00"),
            "iva_credit": Decimal("11.70"),
            "iva_perceived": Decimal("0.00"),
            "total": Decimal("101.70"),
            "payment_condition": "CREDIT",
            "due_date": date(2026, 11, 15),
            "amount_paid": Decimal("101.70"),
            "payment_status": "PAID",
            "status": "REGISTERED",
            "journal_entry": entry_3,
            "notes": "Reactivos químicos de formulación profesional para estilistas.",
            "created_by": creator,
        },
    )
    if created_p2:
        PurchaseLine.objects.create(
            purchase=p2,
            line_no=1,
            product=prod_map["CAB-002"],
            location=loc_map["CAB2"],
            description="Acondicionador sellador PH Acidifying y peróxidos para Cabina",
            quantity=Decimal("5.000"),
            unit_cost=Decimal("18.0000"),
            taxable_amount=Decimal("90.00"),
            iva_amount=Decimal("11.70"),
        )

    if acc_caja and entry_7 and not SupplierPayment.objects.filter(purchase=p2).exists():
        SupplierPayment.objects.create(
            purchase=p2,
            payment_date=date(2026, 11, 8),
            amount=Decimal("101.70"),
            payment_method="CASH",
            reference="Recibo de caja #0042",
            cash_account=acc_caja,
            journal_entry=entry_7,
            created_by=creator,
        )

    p3, created_p3 = Purchase.objects.update_or_create(
        supplier=sup_color,
        doc_type="CCF",
        doc_number="CCF-4530",
        defaults={
            "doc_date": date(2026, 11, 3),
            "period": nov_period,
            "destination": "CABINA",
            "taxable_amount": Decimal("60.00"),
            "exempt_amount": Decimal("0.00"),
            "iva_credit": Decimal("7.80"),
            "iva_perceived": Decimal("0.00"),
            "total": Decimal("67.80"),
            "payment_condition": "CREDIT",
            "due_date": date(2026, 11, 30),
            "amount_paid": Decimal("0.00"),
            "payment_status": "PENDING",
            "status": "REGISTERED",
            "journal_entry": entry_3,
            "notes": "Gama de tintes sin amoniaco recién transferida a estaciones.",
            "created_by": creator,
        },
    )
    if created_p3:
        PurchaseLine.objects.create(
            purchase=p3,
            line_no=1,
            product=prod_map["CAB-001"],
            location=loc_map["CAB1"],
            description="Tintes orgánicos Majirel Tubos 50ml (Gama Castaños)",
            quantity=Decimal("4.000"),
            unit_cost=Decimal("15.0000"),
            taxable_amount=Decimal("60.00"),
            iva_amount=Decimal("7.80"),
        )


def unseed_inventory_and_purchases(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0002_initial"),
        ("purchases", "0001_initial"),
        ("sales", "0001_initial_and_seed"),
        ("accounting", "0001_initial_and_seed"),
        ("core", "0002_core_domain_and_seed"),
    ]

    operations = [
        migrations.RunPython(install_triggers_and_views, remove_triggers_and_views),
        migrations.RunPython(seed_inventory_and_purchases, unseed_inventory_and_purchases),
    ]
