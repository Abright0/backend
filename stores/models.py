from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_migrate
from accounts.models import User

class Store(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @classmethod
    def initialize_stores(cls):
        stores = [
            {'name': 'McKinney', 'address': '___', 'phone': '(___) ___-____'},
            {'name': 'Frisco', 'address': '______', 'phone': '(___) ___-____'},
            {'name': 'Propser', 'address': '______', 'phone': '(___) ___-____'},
            {'name': 'Denton', 'address': '______', 'phone': '(___) ___-____'},
        ]
        
        for store_data in stores:
            cls.objects.get_or_create(
                name=store_data['name'],
                defaults={
                    'address': store_data['address'],
                    'phone': store_data['phone']
                }
            )

@receiver(post_migrate)
def create_stores(sender, **kwargs):
    Store.initialize_stores()