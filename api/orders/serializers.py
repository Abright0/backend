# /backend/api/orders/serializers.py
from rest_framework import serializers
from orders.models import Order, OrderItem
from stores.models import Store

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
            'preferred_delivery_time', 'delivery_instructions',
            'notes', 'creation_date', 'delivery_date', 
            'store', 'store_name', 'status', 'driver', 'items'
        ]
    
    def get_status(self, obj):
        """
        Get the status from the most recent assignment.
        Map backend status values to frontend-friendly display values.
        """
        # Check if prefetched assignments are available
        assignments = getattr(obj, 'prefetched_assignments', None)
        
        if not assignments and hasattr(obj, 'assignments'):
            try:
                # Get the latest assignment if prefetch wasn't used
                assignment = obj.assignments.latest('id')
                status_value = assignment.status
            except:
                return "Order Placed"  # Default status if no assignments
        elif assignments:
            # Use the prefetched assignment if available
            status_value = assignments[-1].status if assignments else "order_placed"
        else:
            return "Order Placed"
        
        # Map backend status codes to frontend display values
        status_mapping = {
            ('order_placed', 'Order Placed'),
            ('accepted_by_driver', 'Accepted by Driver(s)'),
            ('en_route', 'En Route'),
            ('complete', 'Complete'),
            ('misdelivery', 'Misdelivery'),
            ('rescheduled','Rescheduled'),
            ('canceled', 'Canceled'),
        }
        
        return status_mapping.get(status_value, status_value)
    
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
    """
    Detailed Order serializer for individual order views.
    Includes related order items and more details.
    """
    store_details = StoreSerializer(source='store', read_only=True)
    
    class Meta:
        model = Order
        fields = OrderSerializer.Meta.fields + [
            'store_details', 'customer_num',
            'misdelivery_reason'
        ]