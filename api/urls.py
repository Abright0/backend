from django.urls import path, include

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api.accounts.views import UserViewSet
from api.stores.views import StoreViewSet
from api.products.views import ProductListCreate, ProductImportView, SearchProductView
from api.orders.views import OrderViewSet
from api.assignments.views import AssignmentViewSet

from api.views import LogoutView

from django.conf import settings
from django.conf.urls.static import static


# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'stores', StoreViewSet)
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'assignments', AssignmentViewSet)

# API URL configuration
urlpatterns = [
    path('', include(router.urls)),
    path('login/', TokenObtainPairView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('logout/', LogoutView.as_view()),
    # DELETE LATER
    path('products/', ProductListCreate.as_view(), name='product-list-create'),
    path('import-products/', ProductImportView.as_view(), name="import-products"),
    path('search-product/', SearchProductView.as_view(), name="search-product"),
    path(r'api/users/me/', UserViewSet.as_view({'get':'me'})),
    path(r'api/users/me/stores/', UserViewSet.as_view({'get':'my_stores'})),
    ]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)