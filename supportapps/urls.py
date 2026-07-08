from django.urls import path
from .views import SupportTicketCreateView,SupportTicketDetailView,SupportMessageCreateView

urlpatterns = [
    path("tickets/",
SupportTicketCreateView.as_view(),
name="support-tickets"),
path("ticketsm/<int:pk>/",
     SupportTicketDetailView.as_view(),
     name="support-ticket-detail"),
     path(
         "tickets/<int:pk>/messages/",
         SupportMessageCreateView.as_view(),
         name="support-message",
     ),
]