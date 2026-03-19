from django.contrib import admin
from .models import Category, Product, StockMovement, LowStockAlert


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    list_filter = ("name",)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "sku", "cost_price", "selling_price", "stock_quantity", "is_active")
    search_fields = ("name", "sku")
    list_filter = ("category", "is_active")

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "movement_type", "created_at")
    search_fields = ("product__name",)
    list_filter = ("movement_type", "created_at")


@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    list_display = ("product", "threshold_value", "stock_quantity_at_trigger", "is_active", "created_at")
    search_fields = ("product__name", "product__sku")
    list_filter = ("is_active", "created_at")
