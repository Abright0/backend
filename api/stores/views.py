from django.shortcuts import render

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from stores.models import Store

from .serializers import StoreSerializer
from api.accounts.serializers import UserSerializer

class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]

    """
    Helper Methods
    """

    # api/stores/{store_id}/users/
    # Get all Users for a specific store
    # FURTHER DEVELOPMENT - FILTER BY ROLE
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        store = self.get_object()
        users = store.store_users.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
