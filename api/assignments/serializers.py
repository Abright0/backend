# api/assignments/serializers.py
from rest_framework import serializers
from assignments.models import DeliveryAttempt, ScheduledItem, DeliveryPhoto
from assignments.utils import generate_signed_url

class ScheduledItemSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ScheduledItem
        fields = '__all__'

class DeliveryAttemptSerializer(serializers.ModelSerializer):
    scheduled_items = ScheduledItemSerializer(many=True, required=False)

    class Meta:
        model = DeliveryAttempt
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make fields optional so validation doesn't block create()
        self.fields['delivery_time'].required = False
        self.fields['delivery_date'].required = False
        self.fields['drivers'].required = False
        self.fields['order'].required = False  # Since we inject this from context

    def validate(self, data):
        return data

    def create(self, validated_data):
        print("CREATE CUSTOM")
        scheduled_items_data = validated_data.pop('scheduled_items', [])
        order = self.context.get('order')

        if not order:
            raise serializers.ValidationError("Order is required to create a delivery attempt.")

        is_first_attempt = not DeliveryAttempt.objects.filter(order=order).exists()
        print("Is first attempt")
        print(is_first_attempt)

        if is_first_attempt:
            validated_data.setdefault('delivery_date', order.delivery_date)
            validated_data.setdefault('delivery_time', order.preferred_delivery_time)
        else:
            # Validate that required fields are explicitly provided
            missing = []
            for field in ['delivery_date', 'delivery_time']:
                if field not in validated_data:
                    missing.append(field)
            if missing:
                raise serializers.ValidationError({f: 'This field is required.' for f in missing})

        validated_data["order"] = order  # Explicitly set this since it’s not in the payload
        validated_data.setdefault("status", "order_placed")
        delivery_attempt = DeliveryAttempt.objects.create(**validated_data)

        for item_data in scheduled_items_data:
            ScheduledItem.objects.create(delivery_attempt=delivery_attempt, **item_data)

        return delivery_attempt



    def update(self, instance, validated_data):
        previous_status = instance.status
        new_status = validated_data.get('status', previous_status)

        # Block status change to 'complete' if no photos
        if new_status == 'complete' and not instance.has_required_photos():
            raise serializers.ValidationError("Cannot mark as complete: delivery photos are required.")

        # Block status change to 'en_route' if arrival data missing
        mins = validated_data.get('mins_to_arrival') or instance.mins_to_arrival
        miles = validated_data.get('miles_to_arrival') or instance.miles_to_arrival

        if new_status == 'en_route' and (not mins or not miles):
            raise serializers.ValidationError("Cannot mark as en route: arrival time and distance must be provided.")

        # Proceed with update
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        current_status = instance.status
        store = instance.order.store

        # Status → Event mapping
        status_event_map = {
            'assigned_to_driver': 'assigned_to_driver',
            'accepted_by_driver': 'drive_preparing',
            'en_route': 'driver_en_route',
            'complete': 'driver_complete',
            'misdelivery': 'driver_misdelivery',
            'rescheduled': 'driver_rescheduled',
            'canceled': 'driver_canceled',
        }

        event_type = status_event_map.get(current_status)
        if event_type:
            should_send = True

            # Extra SMS send safeguard
            if current_status == 'complete' and not instance.has_required_photos():
                should_send = False
            if current_status == 'en_route' and (not instance.mins_to_arrival or not instance.miles_to_arrival):
                should_send = False

            if should_send:
                self.send_status_sms(instance, event_type)

        return super().update(instance, validated_data)

    def build_context_for_event(self, attempt, event_type):
        order = attempt.order
        context = {
            "customer_name": order.customer.name,
            "order_id": order.invoice_num,
            "phone_number": order.customer.phone_number,
        }

        if event_type == 'driver_en_route':
            if attempt.mins_to_arrival:
                context["mins_to_arrival"] = attempt.mins_to_arrival
            if attempt.miles_to_arrival:
                context["miles_to_arrival"] = attempt.miles_to_arrival

        elif event_type == 'driver_complete':
            photo_qs = attempt.photos.all()
            if photo_qs.exists():
                signed_urls = [generate_signed_url(p.image.name) for p in photo_qs]
                context["photo_links"] = "\n".join(signed_urls)
            else:
                context["photo_links"] = "No delivery photos available."

        return context
            
    def send_status_sms(self, attempt, event_type):
        context = self.build_context_for_event(attempt, event_type)
        trigger_message(event_type, context, attempt.order.store)

class DeliveryPhotoSerializer(serializers.ModelSerializer):
    signed_url = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryPhoto
        fields = ['id', 'caption', 'image', 'signed_url', 'delivery_attempt']

    def get_signed_url(self, obj):
        return generate_signed_url(obj.image.name)