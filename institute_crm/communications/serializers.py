from rest_framework import serializers
from communications.models import (
    Announcement,
    DeviceToken,
    Notification,
    WhatsAppDelivery,
    WhatsAppPreference,
    WhatsAppTemplate,
)
from communications.phone_utils import normalize_phone_number

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
            'title', 'message', 'channel', 'is_read', 'campaign_id', 'created_at',
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
        choices=['IN_APP', 'EMAIL', 'SMS', 'WHATSAPP', 'ALL'], default='IN_APP'
    )
    target_audience = serializers.ChoiceField(
        choices=['STUDENTS', 'PARENTS', 'ALL'], default='STUDENTS'
    )
    template_key = serializers.CharField(required=False, allow_blank=True, default='')
    template_parameters = serializers.DictField(required=False, default=dict)


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


class WhatsAppPreferenceSerializer(serializers.ModelSerializer):
    whatsapp_phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = WhatsAppPreference
        fields = [
            'id', 'whatsapp_phone', 'is_whatsapp_verified',
            'opt_in_transactional', 'opt_in_marketing',
            'consent_source', 'consent_ip_address',
            'opted_out_at', 'opt_out_reason', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_whatsapp_verified', 'opted_out_at', 'opt_out_reason', 'created_at', 'updated_at']

    def validate_whatsapp_phone(self, value):
        if value in (None, ''):
            return None
        normalized = normalize_phone_number(value)
        if normalized is None:
            raise serializers.ValidationError('Enter a valid phone number (E.164, e.g. +919876543210).')
        return normalized


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppTemplate
        fields = [
            'id', 'template_key', 'meta_template_name', 'category',
            'language_code', 'header_type', 'body_text_sample',
            'parameter_schema', 'is_active',
        ]


class WhatsAppDeliverySerializer(serializers.ModelSerializer):
    recipient_name = serializers.SerializerMethodField()

    class Meta:
        model = WhatsAppDelivery
        fields = [
            'id', 'recipient', 'recipient_name', 'recipient_role',
            'phone_snapshot', 'template_name', 'template_parameters',
            'status', 'error_code', 'error_message', 'attempt_count',
            'pricing_category', 'estimated_cost',
            'sent_at', 'delivered_at', 'read_at', 'failed_at', 'created_at',
        ]

    def get_recipient_name(self, obj):
        return obj.recipient.get_full_name() or obj.recipient.username


class SendNotificationSerializer(serializers.Serializer):
    batch_id = serializers.UUIDField()
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()
    channel = serializers.ChoiceField(
        choices=['IN_APP', 'EMAIL', 'SMS', 'WHATSAPP', 'ALL'], default='IN_APP'
    )
    target_audience = serializers.ChoiceField(
        choices=['STUDENTS', 'PARENTS', 'ALL'], default='STUDENTS'
    )
    template_key = serializers.CharField(required=False, allow_blank=True, default='')
    template_parameters = serializers.DictField(required=False, default=dict)

    def validate(self, attrs):
        if attrs.get('channel') in ('WHATSAPP', 'ALL') and not attrs.get('template_key'):
            raise serializers.ValidationError(
                {'template_key': 'template_key is required for WhatsApp channel.'}
            )
        return attrs


class AudiencePreviewSerializer(serializers.Serializer):
    batch_id = serializers.UUIDField()
    target_audience = serializers.ChoiceField(
        choices=['STUDENTS', 'PARENTS', 'ALL'], default='STUDENTS'
    )
