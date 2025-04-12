# api/assignments/serializers.py
from rest_framework import serializers
from assignments.models import DeliveryAttempt, ScheduledItem, DeliveryPhoto
from assignments.utils import generate_signed_url

class ScheduledItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledItem
        fields = '__all__'

class DeliveryAttemptSerializer(serializers.ModelSerializer):
    scheduled_items = ScheduledItemSerializer(many=True, read_only=True)

    class Meta:
        model = DeliveryAttempt
        fields = '__all__'

    def update(self, instance, validated_data):
        # Capture status before updating
        previous_status = instance.status

        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Trigger message only when ready, and not yet sent
        if (
            instance.status == 'en_route' and
            instance.mins_to_arrival and
            instance.miles_to_arrival and
            not instance.arrival_sms_sent
        ):
            self.send_en_route_sms(instance)
            instance.arrival_sms_sent = True
            instance.save(update_fields=['arrival_sms_sent'])

        return instance


    def send_en_route_sms(self, attempt):
        order = attempt.order
        store = order.store  # make sure order has a FK to Store
        phone_number = order.customer.phone_number

        context = {
            "customer_name": order.customer.name,
            "order_id": order.invoice_num,
            "mins_to_arrival": attempt.mins_to_arrival,
            "miles_to_arrival": attempt.miles_to_arrival,
            "phone_number": phone_number,
        }

        trigger_message("driver_en_route", context, store)

class DeliveryPhotoSerializer(serializers.ModelSerializer):
    signed_url = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryPhoto
        fields = ['id', 'caption', 'signed_url']

    def get_signed_url(self, obj):
        return generate_signed_url(obj.image.name)


class DeliveryAttemptSerializer(serializers.ModelSerializer):
    scheduled_items = ScheduledItemSerializer(many=True, read_only=True)
    photos = DeliveryPhotoSerializer(many=True, read_only=True)  # <-- Add this line

    class Meta:
        model = DeliveryAttempt
        fields = '__all__'
