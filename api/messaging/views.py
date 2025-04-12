# api/messaging/views.py

from rest_framework import viewsets
from messaging.models import MessageTemplate
from messaging.serializers import MessageTemplateSerializer
from rest_framework.permissions import IsAuthenticated  # customize if needed

class MessageTemplateViewSet(viewsets.ModelViewSet):
    queryset = MessageTemplate.objects.all()
    serializer_class = MessageTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['store__id', 'event']  # or use DjangoFilterBackend for precision