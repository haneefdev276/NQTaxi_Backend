from django.db import models
from django.conf import settings 

STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS","In Progress"),
        ("RESOLVED","Resolved"),
        ("CLOSED","Closed"),
    ]
class SupportTicket(models.Model):
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="OPEN",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )

    subject = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject

class SupportMessage(models.Model):
    ticket = models.ForeignKey(
        "SupportTicket",
        on_delete=models.CASCADE,
        related_name="messages"

    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"{self.ticket.id} - {self.sender}"