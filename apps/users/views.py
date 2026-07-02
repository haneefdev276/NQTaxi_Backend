from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.serializers import RegisterSerializer, UserPublicSerializer, get_public_user_id


def _auth_error_response(exc, status_code):
    if isinstance(exc, AuthenticationFailed):
        detail = exc.detail
    else:
        detail = exc.detail if hasattr(exc, 'detail') else str(exc)

    if isinstance(detail, dict):
        errors = detail
    elif isinstance(detail, list):
        errors = {'non_field_errors': detail}
    else:
        errors = {'non_field_errors': [str(detail)]}

    return Response(
        {
            'success': False,
            'errors': errors,
        },
        status=status_code,
    )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['user_id'] = user.pk
        token['public_user_id'] = get_public_user_id(user)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        from apps.customers.models import RiderProfile
        from apps.notifications.utils import ensure_welcome_notification

        RiderProfile.objects.get_or_create(user=self.user)
        ensure_welcome_notification(self.user)
        return data


@extend_schema(
    tags=['Auth'],
    summary='Register a new rider',
    description='Create a new user account and rider profile.',
)
class RegisterView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()
        public_user_id = get_public_user_id(user)
        refresh = RefreshToken.for_user(user)
        refresh['user_id'] = user.pk
        refresh['public_user_id'] = public_user_id
        access_token = refresh.access_token
        access_token['user_id'] = user.pk
        access_token['public_user_id'] = public_user_id

        return Response(
            {
                'success': True,
                'message': 'User registered successfully',
                'user': UserPublicSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=['Auth'], summary='Obtain JWT access and refresh tokens')
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except AuthenticationFailed as exc:
            return _auth_error_response(exc, status.HTTP_401_UNAUTHORIZED)
        except ValidationError as exc:
            return _auth_error_response(exc, status.HTTP_400_BAD_REQUEST)

        user = serializer.user
        data = serializer.validated_data

        return Response(
            {
                'success': True,
                'message': 'Login successful',
                'user': UserPublicSerializer(user).data,
                'tokens': {
                    'refresh': str(data['refresh']),
                    'access': str(data['access']),
                },
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=['Auth'], summary='Refresh JWT access token')
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except AuthenticationFailed as exc:
            return _auth_error_response(exc, status.HTTP_401_UNAUTHORIZED)
        except ValidationError as exc:
            return _auth_error_response(exc, status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data

        tokens = {
            'access': str(data['access']),
            'refresh': str(data.get('refresh', request.data.get('refresh', ''))),
        }

        return Response(
            {
                'success': True,
                'message': 'Token refreshed successfully',
                'tokens': tokens,
            },
            status=status.HTTP_200_OK,
        )
