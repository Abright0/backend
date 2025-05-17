# backend/assignments/models.py
from django.db import models
from accounts.models import User
from orders.models import Order, OrderItem
import os
from datetime import datetime
from assignments.utils import generate_signed_url

from django.utils import timezone
from datetime import timedelta

def delivery_photo_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1] or ".jpg"  # fallback if no extension
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%S%f')
    return f"delivery_photos/photo_{timestamp}{ext}"


class DeliveryAttempt(models.Model):
    STATUS_CHOICES = [
        ('order_placed', 'Order Placed'),
        ('assigned_to_driver', 'Assigned to Driver(s)'),
        ('accepted_by_driver', 'Accepted by Driver(s)'),
        ('en_route', 'En Route'),
        ('complete', 'Complete'),
        ('misdelivery', 'Misdelivery'),
        ('rescheduled','Rescheduled'),
        ('canceled', 'Canceled'),
    ]

    completion_sms_sent = models.BooleanField(default=False)  # NEW
 
    status_changed_at = models.DateTimeField(auto_now=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='delivery_attempts')
    drivers = models.ManyToManyField(User, related_name='drivers', blank=True)

    mins_to_arrival = models.TextField(blank=True, null=True)
    miles_to_arrival = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)

    delivery_date = models.DateField()
    delivery_time = models.TimeField()
    result = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)


    #def mark_item_issue(self, order_item, issue):
    #    attempted = self.attempted_items.filter(order_item=order_item).first()
    #    if attempted:
    #        attempted.issue = issue
    #        attempted.save()

    def __str__(self):
        return f"Attempt for Order {self.order.invoice_num} - {self.get_status_display()} on {self.delivery_date}"

    def has_required_photos(self):
        """
        Return True if at least one delivery photo exists for this attempt.
        """
        return self.photos.exists()

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
        'assignments.DeliveryAttempt',
        on_delete=models.CASCADE,
        related_name='photos'
    )
    image = models.ImageField(upload_to=delivery_photo_upload_path)
    caption = models.CharField(max_length=255, blank=True)
    upload_at = models.DateTimeField(auto_now_add=True)

    # new fields
    signed_url = models.URLField(blank=True, null=True)
    signed_url_expiry = models.DateTimeField(blank=True, null=True)

    def create_signed_url(self, expiration_minutes=2880):  # 48 hours
        self.signed_url = generate_signed_url(self.image.name, expiration_minutes)
        self.signed_url_expiry = timezone.now() + timedelta(minutes=expiration_minutes)
        self.save()

    def __str__(self):
        return f"Photo for {self.delivery_attempt} - {self.caption or 'No caption'}"