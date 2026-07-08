from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import SupportTicket,SupportMessage
from .serializers import SupportTicketSerializer,SupportMessageSerializer

class SupportTicketCreateView(generics.ListCreateAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)
    
    def perform_create(self,serializer):

        serializer.save(user=self.request.user)
class SupportTicketDetailView(generics.RetrieveAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)    
    
class SupportMessageCreateView(generics.CreateAPIView):
    serializer_class=SupportMessageSerializer
    permission_classes=[IsAuthenticated]

    def perform_create(self, serializer):
        ticket = get_object_or_404(
            SupportTicket,
            id=self.kwargs["pk"],
            user=self.request.user
            )
        
        serializer.save(
            sender=self.request.user,
            ticket=ticket
        )
        