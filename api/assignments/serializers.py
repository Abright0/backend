from rest_framework import serializers
from accounts.models import User
from orders.models import Order
from assignments.models import Assignment


class AssignmentSerializer(serializers.ModelSerializer):
    drivers = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True)
    previous_assignments = serializers.ListField(child=serializers.DictField(), read_only=True)

    class Meta:
        model = Assignment
        fields = ['id', 'order', 'drivers', 'status', 'assigned_delivery_date', 'assigned_delivery_time', 'previous_assignments']
    
    def create(self, validated_data):
        drivers_data = validated_data.pop('drivers', [])
        assignment = Assignment.objects.create(**validated_data)
        assignment.drivers.set(drivers_data)
        assignment.save()
        
        assignment.add_to_history(
            status=assignment.status,
            delivery_date=assignment.assigned_delivery_date,
            delivery_time=assignment.assigned_delivery_time,
            result="Assignment created",
            drivers=assignment.drivers.all()
        )
        return assignment

    def update(self, instance, validated_data):
        drivers_data = validated_data.pop('drivers', None)
        if drivers_data is not None:
            instance.drivers.set(drivers_data) # updates the drivers

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        instance.add_to_history(
            status=instance.status,
            delivery_date=instance.assigned_delivery_date,
            delivery_time=instance.assigned_delivery_time,
            result="Assignment updated",
            drivers=instance.drivers.all()
        )
        return instance