# api/stores/serializers.py
from rest_framework import serializers
from stores.models import Store

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            'id',
            'name',
            'address',
            'phone',
            'store_users',
            'created_at'
        ]
    def get_users(self, obj):
        return [
            {
                'id':user.id,
                'username':user.username,
                'email':user.email
            } for user in obj.users.all()
        ]