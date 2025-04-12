from django.contrib import admin
from orders.models import Order  # Adjust if you have more models

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['invoice_num', 'customer', 'created_at']
    search_fields = ['invoice_num', 'customer__name']
    ordering = ['-created_at']
