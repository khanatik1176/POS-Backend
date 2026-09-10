from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .capabilities import ALL_ACTION_KEYS, CAPABILITY_REGISTRY
from .models import AuditLog, Role
from .permissions import IsSuperUser
from .serializers import AuditLogSerializer, RoleSerializer, UserCreateSerializer, UserSerializer

User = get_user_model()

MAX_LOG_ROWS = 1000


class CapabilitiesAPIView(APIView):
    """The full registry of pages/actions, for the Settings UI to render."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(CAPABILITY_REGISTRY)


class MyPermissionsAPIView(APIView):
    """What the current user can actually do, for the frontend to gate on."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_superuser:
            return Response({'is_superuser': True, 'actions': sorted(ALL_ACTION_KEYS)})
        profile = getattr(user, 'profile', None)
        role = getattr(profile, 'role', None) if profile else None
        return Response({'is_superuser': False, 'actions': (role.actions if role else [])})


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsSuperUser]

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.users.exists():
            return Response(
                {'detail': 'Cannot delete a role that is still assigned to users. Reassign them first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class UserManagementViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().select_related('profile', 'profile__role').order_by('-date_joined')
    permission_classes = [IsSuperUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_superuser:
            return Response({'detail': 'Cannot delete a superuser account.'}, status=status.HTTP_400_BAD_REQUEST)
        if instance.id == request.user.id:
            return Response({'detail': 'Cannot delete your own account.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class AuditLogListAPIView(generics.ListAPIView):
    """Every logged API call: who, from which IP, which endpoint, and the
    outcome. Superuser-only - this is not delegable via roles. Bounded to
    the most recent MAX_LOG_ROWS matches so the payload can never grow
    unbounded; narrow with the query params below to see further back."""
    serializer_class = AuditLogSerializer
    permission_classes = [IsSuperUser]

    def get_queryset(self):
        queryset = AuditLog.objects.all()
        params = self.request.query_params

        username = params.get('username')
        if username:
            queryset = queryset.filter(username__icontains=username)

        method = params.get('method')
        if method:
            queryset = queryset.filter(method__iexact=method)

        path = params.get('path')
        if path:
            queryset = queryset.filter(path__icontains=path)

        ip = params.get('ip')
        if ip:
            queryset = queryset.filter(ip_address__icontains=ip)

        status_code = params.get('status_code')
        if status_code:
            queryset = queryset.filter(status_code=status_code)

        date_from = params.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = params.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset[:MAX_LOG_ROWS]
