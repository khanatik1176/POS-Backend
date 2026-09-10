from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .auth_views import CurrentUserAPIView, SwaggerTokenObtainPairView, SwaggerTokenRefreshView

schema_view = get_schema_view(
    openapi.Info(
        title='Nexora API',
        default_version='v1',
        description='API documentation for Nexora — order & invoice operations',
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

admin.site.site_header = 'Nexora Administration'
admin.site.site_title = 'Nexora Admin'
admin.site.index_title = 'Administration'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', SwaggerTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', SwaggerTokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/me/', CurrentUserAPIView.as_view(), name='current_user'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/', include('orders.urls')),
    path('api/', include('invoices.urls')),
    path('api/', include('accounts.urls')),
] + static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')
