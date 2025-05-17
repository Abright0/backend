# /backend/api/orders/serializers.py
from rest_framework import serializers
from orders.models import Order, OrderItem
from stores.models import Store

from api.assignments.serializers import DeliveryAttemptSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for OrderItem objects.
    """
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name_input', 'quantity', 
            'price_at_order', 'product_mpn'
        ]

class StoreSerializer(serializers.ModelSerializer):
    """
    Simplified Store serializer for inclusion in OrderSerializer.
    """
    class Meta:
        model = Store
        fields = ['id', 'name', 'address']

class OrderSerializer(serializers.ModelSerializer):
    """
    Basic Order serializer for list views.
    Doesn't include related order items to reduce payload size.
    """
    # Expose the store name in addition to the ID
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    # Show order status from the latest assignment
    status = serializers.SerializerMethodField()
    
    # Driver information
    driver = serializers.SerializerMethodField()

    # Include order items
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'invoice_num', 'first_name', 'last_name', 
            'phone_num', 'address', 'customer_email', 
            'notes', 'creation_date', 'delivery_date',
            'store', 'store_name', 'driver', 'items', 'status', 'customer_num'
        ]
    
    def get_status(self, obj):
        latest_attempt = obj.delivery_attempts.order_by('-id').first()  # or '-created_at'
        if not latest_attempt:
            return "Order Placed"  # Default fallback

        status_mapping = {
            'order_placed': 'Order Placed',
            'assigned_to_driver': 'Assigned to Driver(s)',
            'accepted_by_driver': 'Accepted by Driver(s)',
            'en_route': 'En Route',
            'complete': 'Complete',
            'misdelivery': 'Misdelivery',
            'rescheduled': 'Rescheduled',
            'canceled': 'Canceled',
        }

        return status_mapping.get(latest_attempt.status, latest_attempt.status)

    
    def get_driver(self, obj):
        """
        Get the driver name from the assignment.
        """
        # Check if prefetched assignments are available
        assignments = getattr(obj, 'prefetched_assignments', None)
        
        if not assignments and hasattr(obj, 'assignments'):
            try:
                # Get the latest assignment if prefetch wasn't used
                assignment = obj.assignments.latest('id')
                drivers = assignment.drivers.all()
                if drivers.exists():
                    driver = drivers.first()
                    return f"{driver.first_name} {driver.last_name}".strip() or driver.username
            except:
                return None
        elif assignments and assignments:
            # Use the prefetched assignment if available
            latest_assignment = assignments[-1]
            drivers = latest_assignment.drivers.all()
            if drivers.exists():
                driver = drivers.first()
                return f"{driver.first_name} {driver.last_name}".strip() or driver.username
        
        return None

class OrderDetailSerializer(OrderSerializer):
    delivery_attempts = DeliveryAttemptSerializer(many=True, required=False)
    store_details = StoreSerializer(source='store', read_only=True)

    class Meta:
        model = Order
        fields = OrderSerializer.Meta.fields + [
            'store_details',
            'customer_num',
            'misdelivery_reason',
            'delivery_attempts'
        ]

    def update(self, instance, validated_data):
        delivery_attempts_data = validated_data.pop('delivery_attempts', None)

        # Update basic order fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or create delivery attempts
        if delivery_attempts_data is not None:
            self._update_delivery_attempts(instance, delivery_attempts_data)

        return instance

    def _update_delivery_attempts(self, order, attempts_data):
        for attempt_data in attempts_data:
            attempt_id = attempt_data.get('id')

            if attempt_id:
                try:
                    instance = order.delivery_attempts.get(id=attempt_id)
                    serializer = DeliveryAttemptSerializer(
                        instance,
                        data=attempt_data,
                        partial=True,
                        context={'order': order}
                    )
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                except DeliveryAttempt.DoesNotExist:
                    raise serializers.ValidationError(
                        f"DeliveryAttempt with id {attempt_id} not found."
                    )
            else:
                serializer = DeliveryAttemptSerializer(
                    data=attempt_data,
                    context={'order': order}
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()