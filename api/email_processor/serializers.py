from rest_framework import serializers

class EmailDataSerializer(serializers.Serializer):
    sender = serializers.EmailField()
    subject = serializers.CharField(allow_blank=True, required=False)
    body = serializers.CharField(allow_blank=True, required=False)
    message_id = serializers.CharField(allow_blank=True, required=False)