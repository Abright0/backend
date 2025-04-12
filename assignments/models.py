# backend/assignments/models.py
from django.db import models
from accounts.models import User
from orders.models import Order, OrderItem

class DeliveryAttempt(models.Model):
    STATUS_CHOICES = [
        ('order_placed', 'Order Placed'),
        ('accepted_by_driver', 'Accepted by Driver(s)'),
        ('en_route', 'En Route'),
        ('complete', 'Complete'),
        ('misdelivery', 'Misdelivery'),
        ('rescheduled','Rescheduled'),
        ('canceled', 'Canceled'),
    ]
    status_changed_at = models.DateTimeField(auto_now=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='delivery_attempts')
    drivers = models.ManyToManyField(User, related_name='drivers')
    mins_to_arrival = models.TextField(blank=True, null=True)
    miles_to_arrival = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    delivery_date = models.DateField()
    delivery_time = models.TimeField()
    result = models.TextField(blank=True, null=True)  # e.g., 'no one at address'
    created_at = models.DateTimeField(auto_now_add=True)

    #def mark_item_issue(self, order_item, issue):
    #    attempted = self.attempted_items.filter(order_item=order_item).first()
    #    if attempted:
    #        attempted.issue = issue
    #        attempted.save()

    def __str__(self):
        return f"Attempt for Order {self.order.invoice_num} - {self.get_status_display()} on {self.delivery_date}"

class ScheduledItem(models.Model):
    delivery_attempt = models.ForeignKey(
        DeliveryAttempt,
        on_delete=models.CASCADE,
        related_name='scheduled_items'
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='scheduled_attempts'
    )
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.order_item.product_name_input} - Qty: {self.quantity}"


class DeliveryPhoto(models.Model):
    delivery_attempt = models.ForeignKey(
        DeliveryAttempt,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    image = models.ImageField(upload_to='delivery_photos/') #stored on S3
    caption = models.CharField(max_length=255, blank=True)
    upload_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.delivery_attempt} - {self.caption or 'No caption'}"