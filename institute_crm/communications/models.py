from django.db import models
from institute_crm.utils import BaseModel
from accounts.models import User, Branch, Role

class Announcement(BaseModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='announcements')
    title = models.CharField(max_length=200)
    content = models.TextField()
    target_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    published_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Announcement: {self.title}"


class Notification(BaseModel):
    CHANNEL_CHOICES = [
        ('IN_APP', 'In-App'),
        ('SMS', 'SMS'),
        ('EMAIL', 'Email'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='IN_APP')
    is_read = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"Notification to {self.recipient.username}: {self.title}"
