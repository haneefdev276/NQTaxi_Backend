from random import randint

from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema

from django.utils import timezone

from .models import User
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
    LogoutSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)


# -----------------------------
# Register API
# -----------------------------
class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer


# -----------------------------
# Send OTP API
# -----------------------------
@extend_schema(request=SendOTPSerializer)
class SendOTPView(APIView):

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)

        if serializer.is_valid():
            phone = serializer.validated_data["phone"]

            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            otp = str(randint(100000, 999999))

            user.otp = otp
            user.otp_created_at = timezone.now()
            user.save()

            return Response(
                {
                    "message": "OTP generated successfully.",
                    "otp": otp
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------
# Verify OTP API
# -----------------------------
@extend_schema(request=VerifyOTPSerializer)
class VerifyOTPView(APIView):

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)

        if serializer.is_valid():
            phone = serializer.validated_data["phone"]
            otp = serializer.validated_data["otp"]

            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            if user.otp != otp:
                return Response(
                    {"error": "Invalid OTP"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.is_phone_verified = True
            user.otp = None
            user.save()

            return Response(
                {"message": "Phone verified successfully."},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        identifier = attrs.get('username') or attrs.get('email') or attrs.get('phone')
        password = attrs.get('password')

        if not identifier or not password:
            raise ValidationError({'detail': 'Please provide your email, phone, or username and password.'})

        user = User.objects.filter(username=identifier).first()
        if not user:
            user = User.objects.filter(email__iexact=identifier).first()
        if not user:
            user = User.objects.filter(phone=identifier).first()

        if not user:
            raise ValidationError({'detail': 'No active account found with the given credentials.'})

        attrs['username'] = user.username
        return super().validate(attrs)


# -----------------------------
# Login API
# -----------------------------
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# -----------------------------
# Logout API
# -----------------------------
@extend_schema(request=LogoutSerializer)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)

        if serializer.is_valid():
            try:
                refresh_token = serializer.validated_data["refresh"]
                token = RefreshToken(refresh_token)
                token.blacklist()

                return Response(
                    {"message": "Logout successful."},
                    status=status.HTTP_205_RESET_CONTENT
                )

            except Exception:
                return Response(
                    {"error": "Invalid refresh token."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------
# Forgot Password API
# -----------------------------
@extend_schema(request=ForgotPasswordSerializer)
class ForgotPasswordView(APIView):

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)

        if serializer.is_valid():
            phone = serializer.validated_data["phone"]

            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            otp = str(randint(100000, 999999))

            user.otp = otp
            user.otp_created_at = timezone.now()
            user.save()

            return Response(
                {
                    "message": "Password reset OTP sent successfully.",
                    "otp": otp
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------
# Reset Password API
# -----------------------------
@extend_schema(request=ResetPasswordSerializer)
class ResetPasswordView(APIView):

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)

        if serializer.is_valid():
            phone = serializer.validated_data["phone"]
            otp = serializer.validated_data["otp"]
            new_password = serializer.validated_data["new_password"]

            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            if user.otp != otp:
                return Response(
                    {"error": "Invalid OTP"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(new_password)
            user.otp = None
            user.save()

            return Response(
                {"message": "Password reset successful."},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------
# Current User API
# -----------------------------
class MeView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)