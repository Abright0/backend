# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api.accounts.views import UserViewSet
from api.stores.views import StoreViewSet
from api.products.views import ProductListCreate, ProductImportView, SearchProductView
from api.orders.views import OrderViewSet
from api.assignments.views import (
    DeliveryAttemptViewSet,
    ScheduledItemViewSet,
    DeliveryPhotoViewSet,
)
from api.messaging.views import MessageTemplateViewSet, template_variable_info
from api.views import LogoutView

from django.conf import settings
from django.conf.urls.static import static

# Base router
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'stores', StoreViewSet)
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'messaging/templates', MessageTemplateViewSet, basename='message-template')

# Nested routers
orders_router = NestedDefaultRouter(router, r'orders', lookup='order')
orders_router.register(r'delivery-attempts', DeliveryAttemptViewSet, basename='order-delivery-attempts')

attempts_router = NestedDefaultRouter(orders_router, r'delivery-attempts', lookup='delivery_attempt')
attempts_router.register(r'scheduled-items', ScheduledItemViewSet, basename='scheduleditem')

photos_router = NestedDefaultRouter(orders_router, r'delivery-attempts', lookup='delivery_attempt')
photos_router.register(r'photos', DeliveryPhotoViewSet, basename='deliveryattempt-photos')

# Final URL patterns
urlpatterns = [
    path('', include(router.urls)),
    path('', include(orders_router.urls)),
    path('', include(attempts_router.urls)),
    path('', include(photos_router.urls)),

    path('messaging/template-vars/', template_variable_info, name="template_variable_info"),

    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('products/', ProductListCreate.as_view(), name='product-list-create'),
    path('import-products/', ProductImportView.as_view(), name="import-products"),
    path('search-product/', SearchProductView.as_view(), name="search-product"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
