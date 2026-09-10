from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from .capabilities import ALL_ACTION_KEYS
from .models import AuditLog, Role, UserProfile

User = get_user_model()


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'created_at', 'username', 'ip_address', 'method', 'path', 'status_code', 'user_agent', 'duration_ms']


class RoleSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'actions', 'user_count', 'created_at']

    def get_user_count(self, obj):
        return obj.users.count()

    def validate_actions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('actions must be a list.')
        unknown = set(value) - ALL_ACTION_KEYS
        if unknown:
            raise serializers.ValidationError(f'Unknown action keys: {sorted(unknown)}')
        return value


class UserSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(
        source='profile.role', queryset=Role.objects.all(), required=False, allow_null=True,
    )
    role_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_active', 'is_superuser', 'date_joined', 'role', 'role_name']
        read_only_fields = ['id', 'is_superuser', 'date_joined']

    def get_role_name(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.role.name if profile and profile.role else None

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        instance = super().update(instance, validated_data)
        if profile_data is not None and 'role' in profile_data:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            profile.role = profile_data['role']
            profile.save(update_fields=['role', 'updated_at'])
        return instance


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('A user with that username already exists.')
        return value

    def create(self, validated_data):
        role = validated_data.pop('role', None)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.password = make_password(password)
        user.save()
        UserProfile.objects.create(user=user, role=role)
        return user
