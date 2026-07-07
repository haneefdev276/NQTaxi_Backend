from rest_framework import serializers
from .models import User


# -----------------------------
# Register Serializer
# -----------------------------
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'role', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            phone=validated_data['phone'],
            role=validated_data['role'],
            password=validated_data['password']
        )
        return user


# -----------------------------
# User Serializer
# -----------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'role']


# -----------------------------
# Send OTP Serializer
# -----------------------------
class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)


# -----------------------------
# Verify OTP Serializer
# -----------------------------
class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)


# -----------------------------
# Logout Serializer
# -----------------------------
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


# -----------------------------
# Forgot Password Serializer
# -----------------------------
class ForgotPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)


# -----------------------------
# Reset Password Serializer
# -----------------------------
class ResetPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)