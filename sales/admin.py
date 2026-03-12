from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ("subtotal",)

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "created_by", "total_amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("created_by__username",)
    inlines = [SaleItemInline]