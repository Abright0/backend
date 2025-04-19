# backend/api/orders/views.py
from django.db import transaction
from django.db.models import Q, Prefetch

from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from django_filters.rest_framework import DjangoFilterBackend
from orders.models import Order, OrderItem
from products.models import Product
from stores.models import Store
from .serializers import OrderSerializer, OrderDetailSerializer
from assignments.models import DeliveryAttempt

class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing orders with server-side filtering, sorting, and pagination.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['store_id']
    search_fields = [
        'invoice_num', 'first_name', 'last_name', 'phone_num', 'address',
        'customer_email', 'customer_num', 'delivery_instructions', 'notes',
        'driver', 'assignments__status'
    ]
    ordering_fields = ['creation_date', 'delivery_date', 'assignments_status']
    ordering = ['-creation_date']  # Default ordering

    def get_serializer_class(self):
        """
        Return different serializers for list vs detail views.
        """
        if self.action == 'list' and self.request.query_params.get('view') == 'list':
            return OrderSerializer
        else:
            return OrderDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.prefetch_related('delivery_attempts')

        if self.action == 'list' and self.request.query_params.get('view') == 'list':
            queryset = queryset.select_related('store').prefetch_related(
                Prefetch('delivery_attempts', to_attr='prefetched_attempts')
            )
        else:
            queryset = queryset.select_related('store').prefetch_related(
                'items',
                Prefetch('delivery_attempts', to_attr='prefetched_attempts')
            )

        if not user.is_superuser:
            accessible_stores = user.stores.all()
            if user.is_driver:
                driver_orders = Order.objects.filter(delivery_attempts__drivers=user)
                user_store_orders = Order.objects.filter(store__in=accessible_stores)
                queryset = (driver_orders | user_store_orders).distinct()
            else:
                queryset = queryset.filter(store__in=accessible_stores)

        store_id = self.kwargs.get('store_pk') or self.request.query_params.get('store_id')
        if store_id:
            if not user.is_superuser and not user.stores.filter(id=store_id).exists():
                return Order.objects.none()
            queryset = queryset.filter(store_id=store_id)

        status = self.request.query_params.get('status')
        if status and status != 'all':
            status_mapping = {
                'Order Placed': 'order_placed',
                'Assigned': 'accepted_by_driver',
                'En Route': 'en_route',
                'Completed': 'complete',
                'Misdelivery': 'misdelivery',
                'Rescheduled': 'rescheduled',
                'Canceled': 'canceled',
            }
            if status in status_mapping:
                queryset = queryset.filter(delivery_attempts__status=status_mapping[status])

        return queryset


    def list(self, request, *args, **kwargs):
        """
        Override list method to add order status from assignments.
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new order with associated items.
        """
        data = request.data
        
        try:
            with transaction.atomic():
                # Get the Store instance using the store ID
                store_id = self.kwargs.get("store_pk") or data.get("store_id") or data.get("store")
                try:
                    store = Store.objects.get(pk=store_id)
                except Store.DoesNotExist:
                    return Response(
                        {"error": f"Store with ID {store_id} does not exist."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Ensure user has access to this store
                if not request.user.is_superuser:
                    if not request.user.stores.filter(id=store.id).exists():
                        return Response(
                            {"error": "You don't have permission to create orders for this store."},
                            status=status.HTTP_403_FORBIDDEN
                        )
                
                # Create order directly with Store instance
                order = Order.objects.create(
                    invoice_num=data.get("invoice_num", ""),
                    first_name=data.get("first_name", ""),
                    last_name=data.get("last_name", ""),
                    phone_num=data.get("phone_num", ""),
                    address=data.get("address", ""),
                    customer_email=data.get("customer_email", ""),
                    customer_num=data.get("customer_num", ""),
                    preferred_delivery_time=data.get("preferred_delivery_time"),
                    delivery_instructions=data.get("delivery_instructions", ""),
                    notes=data.get("notes", ""),
                    misdelivery_reason=data.get("misdelivery_reason", ""),
                    store=store,  # Use the actual Store object, not the ID
                    delivery_date=data.get("delivery_date")
                )
                
                # Support both 'products' and 'items' arrays for backward compatibility
                items_data = data.get("products", []) or data.get("items", [])
                
                for item_data in items_data:
                    # Extract all possible field names for better compatibility
                    product_name = (
                        item_data.get("product_name") or 
                        item_data.get("product_name_input") or 
                        "Unnamed Product"
                    )
                    
                    quantity = item_data.get("quantity", 1)
                    
                    price = (
                        item_data.get("price_at_order") or 
                        item_data.get("price") or 
                        0
                    )
                    
                    product_mpn = item_data.get("product_mpn", "")
                    
                    # Create OrderItem with field names that match your model
                    OrderItem.objects.create(
                        order=order,
                        product_name_input=product_name,
                        product_mpn=product_mpn,
                        quantity=quantity,
                        price_at_order=price
                    )
                
                # Create initial assignment with status 'Order Placed'
                #from orders.models import Assignment
                from datetime import datetime, time
                
                # Use provided delivery date or default to today
                delivery_date = data.get("delivery_date") or datetime.now().date()
                
                # Use provided preferred time or default to noon
                delivery_time = data.get("preferred_delivery_time") or time(12, 0)
                '''
                    DeliveryAttempt.objects.create(
                        order=order,
                        status='order_placed',
                        delivery_date=delivery_date,
                        delivery_time=delivery_time
                    )
                '''
                
                # Return the serialized order with detail serializer
                return Response(
                    OrderDetailSerializer(order).data, 
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        order = self.get_object()

        if not request.user.is_superuser:
            if not request.user.stores.filter(id=order.store.id).exists():
                return Response(
                    {"error": "You don't have permission to update orders for this store."},
                    status=status.HTTP_403_FORBIDDEN
                )

        new_store_id = request.data.get('store_id') or request.data.get('store')
        if new_store_id and str(order.store.id) != str(new_store_id):
            try:
                new_store = Store.objects.get(pk=new_store_id)
                if not request.user.is_superuser and not request.user.stores.filter(id=new_store.id).exists():
                    return Response(
                        {"error": "You don't have permission to move orders to this store."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Store.DoesNotExist:
                return Response(
                    {"error": f"Store with ID {new_store_id} does not exist."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Handle delivery attempt status update if provided
        new_status = request.data.get('status')
        if new_status:
            try:
                status_mapping = {
                    'Order Placed': 'order_placed',
                    'Assigned': 'accepted_by_driver',
                    'En Route': 'en_route',
                    'Completed': 'complete',
                    'Misdelivery': 'misdelivery',
                    'Rescheduled': 'rescheduled',
                    'Canceled': 'canceled',
                }
                delivery_attempt = order.delivery_attempts.order_by('-created_at').first()
                if new_status in status_mapping:
                    mapped_status = status_mapping[new_status]
                    if delivery_attempt and delivery_attempt.status != mapped_status:
                        delivery_attempt.status = mapped_status
                        delivery_attempt.save()
            except Exception as e:
                print(f"Error updating delivery attempt status: {e}")

        return super().update(request, *args, **kwargs)