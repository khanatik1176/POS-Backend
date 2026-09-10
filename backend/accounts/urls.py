from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AuditLogListAPIView, CapabilitiesAPIView, MyPermissionsAPIView, RoleViewSet, UserManagementViewSet

router = DefaultRouter()
router.register('rbac/roles', RoleViewSet, basename='rbac-roles')
router.register('rbac/users', UserManagementViewSet, basename='rbac-users')

urlpatterns = [
    path('rbac/capabilities/', CapabilitiesAPIView.as_view(), name='rbac-capabilities'),
    path('rbac/my-permissions/', MyPermissionsAPIView.as_view(), name='rbac-my-permissions'),
    path('rbac/logs/', AuditLogListAPIView.as_view(), name='rbac-logs'),
    path('', include(router.urls)),
]
