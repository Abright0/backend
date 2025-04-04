from django.db import models

class Product(models.Model):
    # Basic product info
    name = models.CharField(max_length=255, blank=True, null=True)  # <title> inside <item>
    description = models.TextField(blank=True, null=True)  # <description>
    
    # Google-specific fields (namespace g)
    condition = models.CharField(max_length=50, blank=True, null=True)  # <g:condition>
    google_id = models.CharField(max_length=255, unique=True, blank=True, null=True)  # <g:id> as CharField
    image_link = models.URLField(blank=True, null=True)  # <g:image_link>
    quantity = models.PositiveIntegerField(default=0, blank=True, null=True)  # <g:quantity>
    sell_on_google_quantity = models.PositiveIntegerField(default=0, blank=True, null=True)  # <g:sell_on_google_quantity>
    availability = models.CharField(max_length=50, blank=True, null=True)  # <g:availability>
    mpn = models.CharField(max_length=50, blank=True, null=True)  # <g:mpn>
    gtin = models.CharField(max_length=50, blank=True, null=True)  # <g:gtin>
    brand = models.CharField(max_length=100, blank=True, null=True)  # <g:brand>
    shipping_weight = models.CharField(max_length=50, blank=True, null=True)  # <g:shipping_weight>
    google_product_category = models.CharField(max_length=255, blank=True, null=True)  # <g:google_product_category>
    product_type = models.CharField(max_length=255, blank=True, null=True)  # <g:product_type>
    
    # Additional link and pricing
    link = models.URLField(blank=True, null=True)  # <link> inside <item>
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # <g:price>



    def __str__(self):
        return self.title
