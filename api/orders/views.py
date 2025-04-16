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
from .serializers import OrderSerializer, OrderDetailSerializer, OrderPhotoSerializer

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
        """
        Return orders that the user has access to based on their store permissions.
        """
        user = self.request.user
        
        # Base queryset with prefetch optimizations
        queryset = Order.objects.prefetch_related('delivery_attempts')
        
        # Optimize querysets with select_related and prefetch_related
        if self.action == 'list' and self.request.query_params.get('view') == 'list':
            # Lighter query for list view
            queryset = queryset.select_related('store')
            
            # Join with assignments to get status
            queryset = queryset.prefetch_related(
                Prefetch('assignments', to_attr='prefetched_assignments')
            )
        else:
            # More detailed query for detail view
            queryset = queryset.select_related('store')
            queryset = queryset.prefetch_related(
                'items',
                Prefetch('assignments', to_attr='prefetched_assignments')
            )
        
        # Filter by stores the user has access to
        if not user.is_superuser:  # Superusers can see all orders
            # Get the stores this user has access to through ManyToManyField
            accessible_stores = user.stores.all()
            
            # If user is a driver, they see orders assigned to them plus orders from their stores
            if user.is_driver:
                driver_orders = Order.objects.filter(assignments__drivers=user)
                user_store_orders = Order.objects.filter(store__in=accessible_stores)
                # Combine both querysets
                queryset = (driver_orders | user_store_orders).distinct()
            else:
                # Regular users only see orders from their accessible stores
                queryset = queryset.filter(store__in=accessible_stores)
        
        # Filter by store_id if provided
        store_id = self.request.query_params.get('store_id')
        if store_id:
            # Verify this user has access to the specified store
            if not user.is_superuser:
                if not user.stores.filter(id=store_id).exists():
                    # If user doesn't have access to this store, return empty queryset
                    return Order.objects.none()
            
            queryset = queryset.filter(store_id=store_id)
            
        # Filter by status if provided (map frontend status names to model statuses)
        status = self.request.query_params.get('status')
        if status and status != 'all':
            # Map frontend status names to assignment statuses
            status_mapping = {
                'Order Placed': 'order_placed',
                'Assigned': 'accepted_by_driver',
                'En Route': 'in_progress',
                'Completed': 'complete'
            }
            
            if status in status_mapping:
                queryset = queryset.filter(assignments__status=status_mapping[status])
        
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
                store_id = data.get("store_id") or data.get("store")
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
                    delivery_date=data.get("delivery_date"),
                    hasImage=data.get("hasImage", False)
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
                Assignment.objects.create(
                    order=order,
                    status='order_placed',
                    assigned_delivery_date=delivery_date,
                    assigned_delivery_time=delivery_time
                )'''
                
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
        """
        Update an order with validation for store access.
        """
        order = self.get_object()
        
        # Check if user has permission to update this order's store
        if not request.user.is_superuser:
            if not request.user.stores.filter(id=order.store.id).exists():
                return Response(
                    {"error": "You don't have permission to update orders for this store."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # If updating store, verify user has access to the new store
        new_store_id = request.data.get('store_id') or request.data.get('store')
        if new_store_id and str(order.store.id) != str(new_store_id):
            try:
                new_store = Store.objects.get(pk=new_store_id)
                if not request.user.is_superuser:
                    if not request.user.stores.filter(id=new_store.id).exists():
                        return Response(
                            {"error": "You don't have permission to move orders to this store."},
                            status=status.HTTP_403_FORBIDDEN
                        )
            except Store.DoesNotExist:
                return Response(
                    {"error": f"Store with ID {new_store_id} does not exist."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        # Handle assignment status update if provided
        new_status = request.data.get('status')
        if new_status:
            try:
                # Map frontend status names to assignment statuses
                status_mapping = {
                    'Order Placed': 'order_placed',
                    'Assigned': 'accepted_by_driver',
                    'En Route': 'in_progress',
                    'Completed': 'complete',
                    # Add other status mappings as needed
                }
                
                # Get the current assignment or create one if it doesn't exist
                assignment = order.assignments.latest('id')
                
                # Only update if status is different
                if new_status in status_mapping and assignment.status != status_mapping[new_status]:
                    # Store previous state in history
                    assignment.add_to_history(
                        assignment.status, 
                        assignment.assigned_delivery_date,
                        assignment.assigned_delivery_time,
                        "Updated from frontend",
                        list(assignment.drivers.all())
                    )
                    
                    # Update the assignment with new status
                    assignment.status = status_mapping[new_status]
                    assignment.save()
            except Exception as e:
                # Continue with order update even if assignment update fails
                print(f"Error updating assignment status: {e}")
        
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def photos(self, request, pk=None):
        """
        Get photos associated with an order.
        """
        order = self.get_object()
        
        # In a real implementation, you would fetch photos from a photos model
        # Here we return a dummy response for now
        photos = []
        
        if order.hasImage:
            # Example data - in real app, fetch from database or storage
            photos = [
                {
                    "id": 1,
                    "url": f"https://example.com/orders/{order.id}/photos/1.jpg",
                    "caption": "Delivery Photo",
                    "uploaded_at": "2025-03-22T12:00:00Z"
                }
            ]
        
        return Response(photos)