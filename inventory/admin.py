from django.contrib import admin
from .models import Category, Product, StockMovement


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
