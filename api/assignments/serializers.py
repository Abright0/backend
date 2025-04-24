# api/assignments/serializers.py
from rest_framework import serializers
from assignments.models import DeliveryAttempt, ScheduledItem, DeliveryPhoto
from assignments.utils import generate_signed_url

from messaging.helpers import trigger_message

from django.utils import timezone
from django.conf import settings
from datetime import datetime

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
        print("CREATE delivery attempt")

        scheduled_items_data = validated_data.pop('scheduled_items', [])
        drivers_data = validated_data.pop('drivers', [])  # <-- handle M2M separately
        order = self.context.get('order')

        if not order:
            raise serializers.ValidationError({"order": "This field is required."})

        is_first_attempt = not DeliveryAttempt.objects.filter(order=order).exists()
        print("Is first attempt:", is_first_attempt)

        if is_first_attempt:
            validated_data.setdefault('delivery_date', order.delivery_date)
            validated_data.setdefault('delivery_time', order.preferred_delivery_time)
            if not drivers_data and order.drivers.exists():
                drivers_data = list(order.drivers.all())
        else:
            missing = []
            for field in ['delivery_date', 'delivery_time']:
                if field not in validated_data:
                    missing.append(field)
            if missing:
                raise serializers.ValidationError({f: 'This field is required.' for f in missing})

        validated_data['order'] = order
        validated_data.setdefault("status", "order_placed")
        
        # Save without M2M first
        delivery_attempt = DeliveryAttempt.objects.create(**validated_data)

        # Assign M2M relationships properly
        if drivers_data:
            delivery_attempt.drivers.set(drivers_data)

        for item_data in scheduled_items_data:
            ScheduledItem.objects.create(delivery_attempt=delivery_attempt, **item_data)

        return delivery_attempt

    def update(self, instance, validated_data):
        previous_status = instance.status
        new_status = validated_data.get('status', previous_status)
        print(f"Status changed: {previous_status} -> {new_status}")

        # Block invalid transitions
        if new_status == 'complete' and not instance.has_required_photos():
            raise serializers.ValidationError("Cannot mark as complete: delivery photos are required.")
        if new_status == 'en_route' and (
            not validated_data.get('mins_to_arrival') and not instance.mins_to_arrival or
            not validated_data.get('miles_to_arrival') and not instance.miles_to_arrival
        ):
            raise serializers.ValidationError("Cannot mark as en route: arrival time and distance must be provided.")

        # Separate M2M field
        drivers = validated_data.pop('drivers', None)

        # Update normal fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        print(instance.status)
        
        if drivers is not None:
            instance.drivers.set(drivers)

        # Messaging on status change
        if previous_status != instance.status:
            status_event_map = {
                'order_placed': 'order_placed',
                'assigned_to_driver': 'assigned_to_driver',
                'accepted_by_driver': 'driver_preparing',
                'en_route': 'driver_en_route',
                'complete': 'driver_complete',
                'misdelivery': 'driver_misdelivery',
                'rescheduled': 'driver_rescheduled',
                'canceled': 'driver_canceled',
            }
            event_type = status_event_map.get(instance.status)

            if event_type:
                should_send = True
                if instance.status == 'complete' and not instance.has_required_photos():
                    should_send = False
                if instance.status == 'en_route' and (not instance.mins_to_arrival or not instance.miles_to_arrival):
                    should_send = False

                if should_send:
                    self.send_status_sms(instance, event_type)

        return instance

    def build_context_for_event(self, attempt, event_type):
        order = attempt.order
        context = {
            "customer_name": order.first_name,
            "order_id": order.invoice_num,
            "phone_number": order.phone_num,
        }

        if event_type == 'driver_en_route':
            if attempt.mins_to_arrival:
                context["mins_to_arrival"] = attempt.mins_to_arrival
            if attempt.miles_to_arrival:
                context["miles_to_arrival"] = attempt.miles_to_arrival

        elif event_type == 'driver_complete':
            photo_qs = attempt.photos.all()
            if photo_qs.exists():
                links = []
                print("DEBUG setting is:", settings.DEBUG)
                # Use production domain if not in debug (prod), otherwise localhost
                if settings.DEBUG:
                    domain = "https://localhost:8000"
                else:
                    domain = getattr(settings, "DELIVERY_LINK_DOMAIN", "https://your-production-domain.com")

                print("BEFORE signed_url:", photo_qs[1].signed_url)
                print("BEFORE signed_url_expiry:", photo_qs[1].signed_url_expiry)

                for photo in photo_qs:
                    if not photo.signed_url or not photo.signed_url_expiry or photo.signed_url_expiry < timezone.now():
                        photo.create_signed_url(expiration_minutes=2880)  # 48 hours

                    short_link = f"{domain}/p/{photo.id}"
                    links.append(short_link)

                print("AFTER signed_url:", photo_qs[1].signed_url)

                context["photo_links"] = "\n".join(links)
            else:
                context["photo_links"] = "No delivery photos available."

        return context
            
    def send_status_sms(self, attempt, event_type):
        print("send status sms")
        context = self.build_context_for_event(attempt, event_type)
        trigger_message(event_type, context, attempt.order.store)


class DeliveryPhotoSerializer(serializers.ModelSerializer):
    signed_url = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryPhoto
        fields = ['id', 'caption', 'image', 'signed_url', 'delivery_attempt']

    def get_signed_url(self, obj):
        if obj.signed_url and obj.signed_url_expiry and obj.signed_url_expiry > timezone.now():
            return obj.signed_url
        return None