from django.contrib import admin
from orders.models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['invoice_num', 'get_customer_name', 'creation_date']
    search_fields = ['invoice_num', 'first_name', 'last_name', 'customer_email']
    ordering = ['-creation_date']
    
    def get_customer_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_customer_name.short_description = 'Customer'