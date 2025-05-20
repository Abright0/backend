# /backend/api/orders/serializers.py
from rest_framework import serializers
from orders.models import Order, OrderItem
from stores.models import Store
from assignments.models import DeliveryAttempt

from api.assignments.serializers import DeliveryAttemptSerializer

class DeliveryAttemptWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAttempt
        exclude = ['created_at', 'status_changed_at']  # exclude read-only fields

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
    store_name = serializers.CharField(source='store.name', read_only=True)
    status = serializers.SerializerMethodField()
    latest_driver_names = serializers.SerializerMethodField()
    latest_delivery_date = serializers.SerializerMethodField()
    invoice_pdf = serializers.FileField(required=False, allow_null=True)
    invoice_pdf_signed_url = serializers.CharField(read_only=True)

    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'invoice_num', 'first_name', 'last_name', 
            'phone_num', 'address', 'customer_email', 
            'notes', 'creation_date', 'delivery_date',
            'store', 'store_name', 'latest_driver_names', 'items', 'status',
            'customer_num', 'latest_delivery_date','invoice_pdf','invoice_pdf_signed_url'
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
    
    def get_latest_driver_names(self, obj):
        latest_attempt = obj.delivery_attempts.order_by('-delivery_date', '-id').first()
        if not latest_attempt:
            return []
        return [
            f"{d.first_name} {d.last_name}".strip() or d.username
            for d in latest_attempt.drivers.all()
        ]


    def get_latest_delivery_date(self, obj):
        latest_attempt = obj.delivery_attempts.order_by('-delivery_date', '-id').first()
        return latest_attempt.delivery_date if latest_attempt else None

    def to_representation(self, instance):
        try:
            instance.get_invoice_signed_url()
        except Exception as e:
            # Optional: log or silence depending on your error strategy
            print(f"Signed URL error: {e}")
        return super().to_representation(instance)


class OrderDetailSerializer(OrderSerializer):
    delivery_attempts = DeliveryAttemptWriteSerializer(many=True, required=False)
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