# messaging/serializers.py
from rest_framework import serializers
from messaging.models import MessageTemplate

class MessageTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = ['id', 'store', 'event', 'content', 'active']
