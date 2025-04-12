# backend/messaging/models.py
from django.db import models

class MessageTemplate(models.Model):
    EVENT_CHOICES = [
        ('driver_en_route', 'Driver En Route'),
        ('order_complete', 'Order Complete'),
        ('photos_submitted', 'Photos Submitted'),
        ('redelivery_assigned', 'Redelivery Assigned'),
        # add more as needed
    ]

    event = models.CharField(max_length=50, choices=EVENT_CHOICES, unique=True)
    content = models.TextField(help_text="Use Django template syntax. Ex: 'Hi {{ customer_name }}, your order {{ order_id }} is complete.'")

    def __str__(self):
        return f"{self.get_event_display()}"