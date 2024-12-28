from django.db import models


class Text(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"TextModel {self.id} - {self.status}"
