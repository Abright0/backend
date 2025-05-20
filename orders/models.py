# /backend/orders/models.py
from django.db import models
from stores.models import Store
from products.models import Product
from assignments.utils import generate_signed_url
from django.utils import timezone
from datetime import timedelta

class Order(models.Model):
    invoice_num = models.CharField(max_length=30)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone_num = models.CharField(max_length=20)
    address = models.CharField(max_length=150)
    customer_email = models.EmailField(max_length=150)
    customer_num = models.CharField(max_length=20)
    #preferred_delivery_time = models.TextField(null=True, blank=True)
    #delivery_instructions = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    misdelivery_reason = models.TextField(null=True, blank=True)
    #delivery_date = models.TextField(null=True, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)    
    # one to many
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='orders')
    status_fallback = models.CharField(
        max_length=30, null=True, blank=True, default='order_placed'
    )
    delivery_date_fallback = models.TextField(null=True, blank=True)
    invoice_pdf = models.FileField(
        upload_to='invoices/',
        null=True,
        blank=True,
        help_text="PDF Invoice File"
    )
    invoice_pdf_signed_url = models.URLField(blank=True,null=True)
    invoice_pdf_signed_url_expiry = models.DateTimeField(blank=True, null=True)

    @property
    def status(self):
        attempt = self.delivery_attempts.order_by('-id').first()
        return attempt.status if attempt and attempt.status else self.status_fallback

    @status.setter
    def status(self, value):
        self.status_fallback = value

    @property
    def delivery_date(self):
        attempt = self.delivery_attempts.order_by('-id').first()
        return attempt.delivery_date if attempt and attempt.delivery_date else self.delivery_date_fallback

    @delivery_date.setter
    def delivery_date(self, value):
        self.delivery_date_fallback = value


    def create_invoice_signed_url(self, expiration_minutes=15):  # 48 hours
        if self.invoice_pdf:
            self.invoice_pdf_signed_url = generate_signed_url(self.invoice_pdf.name, expiration_minutes)
            self.invoice_pdf_signed_url_expiry = timezone.now() + timedelta(minutes=expiration_minutes)
            self.save()
        else:
            return None

    def get_invoice_signed_url(self):
        if not self.invoice_pdf:
            return None

        if not self.invoice_pdf_signed_url or timezone.now() > self.invoice_pdf_signed_url_expiry:
            self.create_invoice_signed_url()

        return self.invoice_pdf_signed_url
        
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


