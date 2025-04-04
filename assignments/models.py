from django.db import models
from accounts.models import User
from orders.models import Order

from datetime import date, time

class Assignment(models.Model):
    ORDER_STATUS_CHOICES = [
        ('order_placed', 'Order Placed'),
        ('accepted_by_driver', 'Accepted by Driver(s)'),
        ('en_route', 'En Route'),
        ('complete', 'Complete'),
        ('misdelivery', 'Misdelivery'),
        ('redelivery_assigned', 'Redelivery Assigned'),
        ('redelivery_in_progress', 'Redelivery In Progress'),
        ('redelivery_complete', 'Redelivery Complete'),
        ('canceled', 'Canceled'),
    ]  
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='assignments')
    drivers = models.ManyToManyField(User, related_name='assigned_orders')
    status = models.CharField(max_length=30, choices=ORDER_STATUS_CHOICES, default='order_placed')
    assigned_delivery_date = models.DateField()
    assigned_delivery_time = models.TimeField()
    previous_assignments = models.JSONField(default=list)  # Store history as a list of dictionaries

    def __str__(self):
        return f"Assignment for Order {self.order.id} - Status: {self.get_status_display()}"
    
    def add_to_history(self, status, delivery_date, delivery_time, result, drivers):
            history_entry = {
                'status': status,
                'delivery_date': delivery_date.isoformat() if isinstance(delivery_date, date) else str(delivery_date),
                'delivery_time': delivery_time.strftime('%H:%M:%S') if isinstance(delivery_time, time) else str(delivery_time),
                'result': result,
                'drivers': [driver.id for driver in drivers]
            }
            
            current_history = self.previous_assignments or []
            current_history.append(history_entry)
            self.previous_assignments = current_history
            self.save()

    class Meta:
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'
