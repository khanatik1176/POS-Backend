from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductListAPIView,
    ReferenceSearchAPIView,
    PlatformTypeListAPIView,
    PaymentMethodListAPIView,
    PaymentMediumListAPIView,
    OrderStatusListAPIView,
    CustomerStatusListAPIView,
    TelegramWebhookAPIView,
    OrderViewSet,
)

router = DefaultRouter()
router.register('orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('products/', ProductListAPIView.as_view(), name='products'),
    path('lookups/products/', ProductListAPIView.as_view(), name='lookup-products'),
    path('references/', ReferenceSearchAPIView.as_view(), name='reference-search'),
    path('lookups/platform-types/', PlatformTypeListAPIView.as_view(), name='platform-types'),
    path('lookups/payment-methods/', PaymentMethodListAPIView.as_view(), name='payment-methods'),
    path('lookups/payment-mediums/', PaymentMediumListAPIView.as_view(), name='payment-mediums'),
    path('lookups/order-statuses/', OrderStatusListAPIView.as_view(), name='order-statuses'),
    path('lookups/customer-statuses/', CustomerStatusListAPIView.as_view(), name='customer-statuses'),
    path('telegram/webhook/', TelegramWebhookAPIView.as_view(), name='telegram-webhook'),
    path('', include(router.urls)),
]
