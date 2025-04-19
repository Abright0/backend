# api/assignments/views.py
from rest_framework import viewsets, status
from .serializers import DeliveryAttemptSerializer, ScheduledItemSerializer, DeliveryPhotoSerializer
from assignments.models import DeliveryAttempt, ScheduledItem
from assignments.models import DeliveryPhoto
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from orders.models import Order

class DeliveryAttemptViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAttempt.objects.all()
    serializer_class = DeliveryAttemptSerializer
    permission_classes = [AllowAny] # or IsAuthenticated

    def get_queryset(self):
        return DeliveryAttempt.objects.filter(order_id=self.kwargs["order_pk"])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        order_id = self.kwargs.get("order_pk")
        if order_id:
            context["order"] = Order.objects.get(id=order_id)
        return context

class ScheduledItemViewSet(viewsets.ModelViewSet):
    queryset = ScheduledItem.objects.all()
    serializer_class = ScheduledItemSerializer
    permission_classes = [AllowAny]  # or IsAuthenticated


class DeliveryPhotoViewSet(viewsets.ModelViewSet):
    queryset = DeliveryPhoto.objects.all()
    serializer_class = DeliveryPhotoSerializer
    http_method_names = ['post', 'get']

    def create(self, request, *args, **kwargs):
        # Detect list of files (bulk upload)
        images = request.FILES.getlist('images')  # key: "images"
        delivery_attempt_id = request.data.get('delivery_attempt')
        caption = request.data.get('caption', '')

        if not images or not delivery_attempt_id:
            return Response({'error': 'Missing images or delivery_attempt'}, status=400)

        uploaded = []
        for image in images:
            photo = DeliveryPhoto.objects.create(
                delivery_attempt_id=delivery_attempt_id,
                image=image,
                caption=caption
            )
            uploaded.append(DeliveryPhotoSerializer(photo, context={'request': request}).data)

        return Response(uploaded, status=status.HTTP_201_CREATED)