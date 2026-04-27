from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})


class LoginResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()


class RefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()


class SwaggerTokenObtainPairView(TokenObtainPairView):
    @swagger_auto_schema(request_body=LoginRequestSerializer, responses={200: LoginResponseSerializer})
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class SwaggerTokenRefreshView(TokenRefreshView):
    @swagger_auto_schema(request_body=RefreshRequestSerializer, responses={200: RefreshResponseSerializer})
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
