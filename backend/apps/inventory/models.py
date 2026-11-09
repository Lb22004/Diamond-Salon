from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Category(models.Model):
    class InventoryType(models.TextChoices):
        VITRINA = "VITRINA", "Vitrina (Para la venta)"
        CABINA = "CABINA", "Cabina (Insumo de servicio)"

    name = models.CharField(max_length=80)
    inventory_type = models.CharField(max_length=10, choices=InventoryType.choices)

    class Meta:
        db_table = "inventory_category"
        ordering = ["inventory_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "inventory_type"],
                name="ux_inventory_category_name_type",
            ),
            models.CheckConstraint(
                condition=Q(inventory_type__in=["VITRINA", "CABINA"]),
                name="ck_inventory_category_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.inventory_type})"


class Location(models.Model):
    class LocationType(models.TextChoices):
        VITRINA = "VITRINA", "Vitrina Comercial"
        CABINA = "CABINA", "Estación de Cabina"
        WAREHOUSE = "WAREHOUSE", "Bodega General"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=80)
    location_type = models.CharField(max_length=10, choices=LocationType.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "inventory_location"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(location_type__in=["VITRINA", "CABINA", "WAREHOUSE"]),
                name="ck_inventory_location_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Product(models.Model):
    class InventoryType(models.TextChoices):
        VITRINA = "VITRINA", "Vitrina (Para la venta)"
        CABINA = "CABINA", "Cabina (Insumo de servicio)"

    class UnitOfMeasure(models.TextChoices):
        UNIT = "UNIT", "Unidad (u)"
        LITER = "LITER", "Litro (L)"
        MILLILITER = "MILLILITER", "Mililitro (ml)"
        GRAM = "GRAM", "Gramo (g)"
        KILOGRAM = "KILOGRAM", "Kilogramo (kg)"
        PACKAGE = "PACKAGE", "Paquete (paq)"

    sku = models.CharField(max_length=30, unique=True)
    barcode = models.CharField(max_length=50, unique=True, null=True, blank=True)
    name = models.CharField(max_length=150)
    brand = models.CharField(max_length=80, null=True, blank=True)
    presentation = models.CharField(max_length=80, null=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    inventory_type = models.CharField(max_length=10, choices=InventoryType.choices)
    unit_of_measure = models.CharField(
        max_length=10,
        choices=UnitOfMeasure.choices,
        default=UnitOfMeasure.UNIT,
    )
    account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        related_name="inventory_products",
    )
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    average_cost = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=Decimal("0.0000"),
    )
    min_stock = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
    )
    default_supplier = models.ForeignKey(
        "purchases.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_products",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_product"
        ordering = ["inventory_type", "sku"]
        constraints = [
            models.CheckConstraint(
                condition=Q(inventory_type__in=["VITRINA", "CABINA"]),
                name="ck_inventory_product_type",
            ),
            models.CheckConstraint(
                condition=Q(average_cost__gte=0) & Q(min_stock__gte=0),
                name="ck_inventory_product_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(inventory_type="CABINA") | Q(sale_price__isnull=False, sale_price__gte=0),
                name="ck_inventory_vitrina_requires_pvp",
            ),
            models.CheckConstraint(
                condition=Q(inventory_type="VITRINA") | Q(sale_price__isnull=True),
                name="ck_inventory_cabina_no_pvp",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sku} - {self.name}"


class Stock(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
    )

    class Meta:
        db_table = "inventory_stock"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "location"],
                name="ux_inventory_stock_product_location",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="ck_inventory_stock_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.sku} @ {self.location.code}: {self.quantity}"


class Adjustment(models.Model):
    class Reason(models.TextChoices):
        PHYSICAL_COUNT = "PHYSICAL_COUNT", "Conteo físico cíclico"
        DAMAGE = "DAMAGE", "Deterioro o rotura en salón"
        EXPIRED = "EXPIRED", "Vencimiento de lote"
        THEFT = "THEFT", "Extravío / Merma"
        OTHER = "OTHER", "Otro ajuste autorizado"

    adjustment_date = models.DateField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    notes = models.TextField(null=True, blank=True)
    journal_entry = models.ForeignKey(
        "accounting.JournalEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_adjustments",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_adjustments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_adjustment"
        ordering = ["-adjustment_date", "-id"]


class Consumption(models.Model):
    consumption_date = models.DateField()
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="consumptions",
    )
    employee = models.ForeignKey(
        "core.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consumptions",
    )
    sale_id = models.BigIntegerField(null=True, blank=True, db_column="sale_id")
    notes = models.TextField(null=True, blank=True)
    journal_entry = models.ForeignKey(
        "accounting.JournalEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_consumptions",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_consumptions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_consumption"
        ordering = ["-consumption_date", "-id"]


class InventoryMovement(models.Model):
    class MovementType(models.TextChoices):
        OPENING = "OPENING", "Saldo inicial de apertura"
        PURCHASE = "PURCHASE", "Entrada por compra (CCF)"
        SALE = "SALE", "Salida por venta retail (Vitrina)"
        CONSUMPTION = "CONSUMPTION", "Consumo técnico en estación (Cabina)"
        ADJUSTMENT_IN = "ADJUSTMENT_IN", "Ajuste positivo (Sobrante)"
        ADJUSTMENT_OUT = "ADJUSTMENT_OUT", "Ajuste negativo (Faltante / Merma)"
        TRANSFER_IN = "TRANSFER_IN", "Entrada por transferencia / reclasificación"
        TRANSFER_OUT = "TRANSFER_OUT", "Salida por transferencia / reclasificación"
        RETURN_IN = "RETURN_IN", "Devolución sobre venta (NC)"
        RETURN_OUT = "RETURN_OUT", "Anulación / devolución sobre compra"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_date = models.DateField()
    movement_type = models.CharField(max_length=15, choices=MovementType.choices)
    direction = models.SmallIntegerField()  # +1 or -1
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=4)
    total_cost = models.DecimalField(max_digits=14, decimal_places=2)
    balance_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    balance_avg_cost = models.DecimalField(max_digits=14, decimal_places=4)
    source_app = models.CharField(max_length=40, null=True, blank=True)
    source_id = models.BigIntegerField(null=True, blank=True)
    journal_entry = models.ForeignKey(
        "accounting.JournalEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_movements",
    )
    notes = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_movement"
        ordering = ["movement_date", "id"]
        indexes = [
            models.Index(
                fields=["product", "movement_date", "id"],
                name="ix_movement_product_date",
            ),
            models.Index(
                fields=["source_app", "source_id"],
                name="ix_movement_source",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(direction__in=[1, -1]),
                name="ck_inventory_movement_direction",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0) & Q(unit_cost__gte=0) & Q(total_cost__gte=0),
                name="ck_inventory_movement_positive",
            ),
        ]
