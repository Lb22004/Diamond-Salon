from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounting.services.posting import get_account
from apps.inventory.models import Category, Location, Product, Stock
from apps.inventory.services import register_movement


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "inventory_type"]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "code", "name", "location_type", "is_active"]


class ProductSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    default_supplier_name = serializers.CharField(source="default_supplier.name", read_only=True, default="")
    initial_quantity = serializers.DecimalField(
        max_digits=12, decimal_places=3, write_only=True, required=False, default=Decimal("0.000")
    )
    initial_location = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "barcode",
            "name",
            "brand",
            "presentation",
            "category",
            "category_name",
            "inventory_type",
            "unit_of_measure",
            "account",
            "account_code",
            "sale_price",
            "average_cost",
            "min_stock",
            "default_supplier",
            "default_supplier_name",
            "is_active",
            "initial_quantity",
            "initial_location",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["account", "created_at", "updated_at"]

    def validate(self, attrs):
        inv_type = attrs.get("inventory_type") or getattr(self.instance, "inventory_type", "VITRINA")
        sale_price = attrs.get("sale_price", getattr(self.instance, "sale_price", None))

        if inv_type == Product.InventoryType.VITRINA:
            if sale_price is None or Decimal(str(sale_price)) <= Decimal("0.00"):
                raise serializers.ValidationError(
                    {"sale_price": "Los productos de Vitrina requieren un PVP unitario mayor a $0.00 (RF-INV-04)."}
                )
        elif inv_type == Product.InventoryType.CABINA:
            attrs["sale_price"] = None

        barcode = attrs.get("barcode")
        if barcode == "":
            attrs["barcode"] = None

        return attrs

    def create(self, validated_data):
        init_qty = validated_data.pop("initial_quantity", Decimal("0.000"))
        init_loc = validated_data.pop("initial_location", "")
        inv_type = validated_data["inventory_type"]
        validated_data["account"] = get_account(
            "INVENTORY_VITRINA" if inv_type == Product.InventoryType.VITRINA else "INVENTORY_CABINA"
        )
        prod = super().create(validated_data)

        if init_qty and init_qty > Decimal("0.000"):
            from datetime import date

            user = self.context["request"].user
            try:
                register_movement(
                    product=prod,
                    location=init_loc or inv_type,
                    movement_type="OPENING",
                    quantity=init_qty,
                    unit_cost=prod.average_cost,
                    movement_date=date.today(),
                    source_app="inventory.product",
                    source_id=prod.pk,
                    notes="Existencia inicial al crear producto",
                    user=user,
                )
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"detail": exc.messages[0] if hasattr(exc, "messages") else str(exc)})
        else:
            default_loc = (
                Location.objects.filter(location_type=inv_type, is_active=True).first()
                or Location.objects.filter(is_active=True).first()
            )
            if default_loc:
                Stock.objects.get_or_create(product=prod, location=default_loc, defaults={"quantity": Decimal("0.000")})

        return prod
