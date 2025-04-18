# backend/messaging.models.py
from django.db import models
from stores.models import Store

class MessageTemplate(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    event = models.CharField(
        max_length=50,
        choices=[
            ('driver_preparing', 'Driver Preparing Delivery'),
            ('driver_en_route', 'Driver En Route'),
            ('driver_complete', 'Delivery Complete'),
            ('driver_misdelivery', 'Misdelivery'),
            ('driver_rescheduled', 'Rescheduled'),
            ('driver_canceled', 'Canceled'),
        ]
    )
    content = models.TextField()
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('store', 'event')

    def __str__(self):
        return f"{self.store.name} - {self.event} ({'Active' if self.active else 'Inactive'})"