# api/messaging/views.py
from rest_framework import viewsets
from messaging.models import MessageTemplate
from .serializers import MessageTemplateSerializer

class MessageTemplateViewSet(viewsets.ModelViewSet):
    queryset = MessageTemplate.objects.all()
    serializer_class = MessageTemplateSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view

TEMPLATE_CONTEXT_VARS = {
    'order_placed': ['customer_name', 'order_id', 'delivery_date'],
    'driver_preparing': ['customer_name', 'order_id', 'delivery_date'],
    'driver_en_route': ['customer_name', 'order_id', 'mins_to_arrival', 'miles_to_arrival', 'delivery_date'],
    'driver_complete': ['customer_name', 'order_id', 'photo_links', 'delivery_date'],
    'driver_misdelivery': ['customer_name', 'order_id', 'delivery_date'],
    'driver_rescheduled': ['customer_name', 'order_id', 'delivery_date'],
    'driver_canceled': ['customer_name', 'order_id', 'delivery_date'],
}

@api_view(['GET'])
def template_variable_info(request):
    return Response(TEMPLATE_CONTEXT_VARS)