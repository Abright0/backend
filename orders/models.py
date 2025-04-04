from django.db import models
from stores.models import Store
from products.models import Product

class Order(models.Model):
    invoice_num = models.CharField(max_length=30)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone_num = models.CharField(max_length=20)
    address = models.CharField(max_length=150)
    customer_email = models.EmailField(max_length=150)
    customer_num = models.CharField(max_length=20)
    preferred_delivery_time = models.TextField(null=True, blank=True)
    delivery_instructions = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    misdelivery_reason = models.TextField(null=True, blank=True)
    delivery_date = models.TextField(null=True, blank=True)
    hasImage = models.BooleanField(null=True, blank=True)

    creation_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)
    
    # one to many
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='orders')

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # Remove product foreign key - items are always custom
    product_name_input = models.CharField(max_length=255, null=True)  # Name of the product
    product_mpn = models.CharField(max_length=100, blank=True)  # Optional MPN
    quantity = models.PositiveIntegerField(default=1)
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.product_name_input} x{self.quantity}"