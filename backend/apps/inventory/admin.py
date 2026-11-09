from django.contrib import admin

from apps.inventory.models import Adjustment, Category, Consumption, InventoryMovement, Location, Product, Stock

admin.site.register(Category)
admin.site.register(Location)
admin.site.register(Product)
admin.site.register(Stock)
admin.site.register(Adjustment)
admin.site.register(Consumption)
admin.site.register(InventoryMovement)
