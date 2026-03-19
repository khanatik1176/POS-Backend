from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductListAPIView, ReferenceSearchAPIView, OrderViewSet

router = DefaultRouter()
router.register('orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('products/', ProductListAPIView.as_view(), name='products'),
    path('references/', ReferenceSearchAPIView.as_view(), name='reference-search'),
    path('', include(router.urls)),
]
