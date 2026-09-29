from rest_framework import serializers
from communications.models import Announcement, DeviceToken, Notification

class AnnouncementSerializer(serializers.ModelSerializer):
    publisher_name = serializers.CharField(source='published_by.get_full_name', read_only=True)

    class Meta:
        model = Announcement
        fields = ['id', 'branch', 'title', 'content', 'target_role', 'published_by', 'publisher_name', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    batch_name = serializers.SerializerMethodField()
    batch_id = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'sender', 'sender_name',
            'batch_id', 'batch_name', 'target_audience',
            'title', 'message', 'channel', 'is_read', 'created_at',
        ]

    def get_sender_name(self, obj):
        sender = getattr(obj, 'sender', None)
        if sender is None:
            return None
        full = sender.get_full_name() if hasattr(sender, 'get_full_name') else ''
        return full or getattr(sender, 'username', None)

    def get_batch_name(self, obj):
        batch = getattr(obj, 'batch', None)
        return getattr(batch, 'name', None) if batch else None

    def get_batch_id(self, obj):
        batch = getattr(obj, 'batch', None)
        return str(batch.pk) if batch and getattr(batch, 'pk', None) else None


class SendBatchNotificationSerializer(serializers.Serializer):
    batch_id = serializers.UUIDField()
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()
    channel = serializers.ChoiceField(
        choices=['IN_APP', 'EMAIL', 'SMS', 'ALL'], default='IN_APP'
    )
    target_audience = serializers.ChoiceField(
        choices=['STUDENTS', 'PARENTS', 'ALL'], default='STUDENTS'
    )


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = [
            'id', 'expo_push_token', 'platform', 'device_name',
            'app_version', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_active', 'created_at', 'updated_at']


class DeviceRegistrationSerializer(serializers.Serializer):
    """Payload posted by the mobile client on every cold start."""

    expo_push_token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=['ios', 'android', 'web'], default='android')
    device_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    app_version = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')
