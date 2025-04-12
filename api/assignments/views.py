# api/assignments/views.py
from rest_framework import viewsets
from .serializers import DeliveryAttemptSerializer, ScheduledItemSerializer, DeliveryPhotoSerializer
from assignments.models import DeliveryAttempt, ScheduledItem
from assignments.models import DeliveryPhoto
from rest_framework.permissions import IsAuthenticated, AllowAny

class DeliveryAttemptViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAttempt.objects.all()
    serializer_class = DeliveryAttemptSerializer
    permission_classes = [AllowAny] # or IsAuthenticated

    def get_queryset(self):
        return DeliveryAttempt.objects.filter(order_id=self.kwargs["order_pk"])

class ScheduledItemViewSet(viewsets.ModelViewSet):
    queryset = ScheduledItem.objects.all()
    serializer_class = ScheduledItemSerializer
    permission_classes = [AllowAny]  # or IsAuthenticated


class DeliveryPhotoViewSet(viewsets.ModelViewSet):
    queryset = DeliveryPhoto.objects.all()
    serializer_class = DeliveryPhotoSerializer
    http_method_names = ['post', 'get']  # Limit to what you need