from django.contrib import admin
from assignments.models import DeliveryAttempt, ScheduledItem

@admin.register(DeliveryAttempt)
class DeliveryAttemptAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'delivery_date', 'mins_to_arrival', 'miles_to_arrival', 'created_at']
    list_filter = ['status', 'delivery_date']
    search_fields = ['order__invoice_num']
    ordering = ['-created_at']

@admin.register(ScheduledItem)
class ScheduledItemAdmin(admin.ModelAdmin):
    list_display = ['order_item', 'delivery_attempt']
    search_fields = ['order_item__name']
