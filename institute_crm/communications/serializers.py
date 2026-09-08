from rest_framework import serializers
from communications.models import Announcement, Notification

class AnnouncementSerializer(serializers.ModelSerializer):
    publisher_name = serializers.CharField(source='published_by.get_full_name', read_only=True)

    class Meta:
        model = Announcement
        fields = ['id', 'branch', 'title', 'content', 'target_role', 'published_by', 'publisher_name', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'title', 'message', 'channel', 'is_read', 'created_at']
