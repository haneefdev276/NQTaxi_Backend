from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import SOSAlert
from .serializers import SOSAlertSerializer


class CreateSOSView(generics.CreateAPIView):
    serializer_class = SOSAlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ListSOSView(generics.ListAPIView):
    queryset = SOSAlert.objects.all().order_by('-created_at')
    serializer_class = SOSAlertSerializer
    permission_classes = [permissions.IsAdminUser]


class ResolveSOSView(generics.UpdateAPIView):
    queryset = SOSAlert.objects.all()
    serializer_class = SOSAlertSerializer
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, *args, **kwargs):
        sos = self.get_object()
        sos.status = 'resolved'
        sos.resolved_at = timezone.now()
        sos.save()

        return Response(
            SOSAlertSerializer(sos).data
        )