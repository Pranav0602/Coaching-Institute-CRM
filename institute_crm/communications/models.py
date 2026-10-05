from django.db import models
from django.conf import settings
from institute_crm.utils import BaseModel
from accounts.models import User, Branch, Role
import uuid

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
        ('WHATSAPP', 'WhatsApp'),
        ('ALL', 'All Channels'),
    ]

    TARGET_AUDIENCE_CHOICES = [
        ('STUDENTS', 'Students'),
        ('PARENTS', 'Parents'),
        ('ALL', 'Students & Parents'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications'
    )
    batch = models.ForeignKey(
        'academics.Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications'
    )
    target_audience = models.CharField(max_length=20, choices=TARGET_AUDIENCE_CHOICES, default='STUDENTS')
    title = models.CharField(max_length=200)
    message = models.TextField()
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='IN_APP')
    is_read = models.BooleanField(default=False, db_index=True)
    # Shared across every Notification row produced by a single send, so the
    # delivery funnel can group recipient rows into one "campaign".
    campaign_id = models.UUIDField(default=uuid.uuid4, db_index=True, editable=False)

    def __str__(self):
        return f"Notification to {self.recipient.username}: {self.title}"


class WhatsAppPreference(BaseModel):
    """Auditable WhatsApp consent, phone preferences, and suppression status."""

    CONSENT_SOURCE_CHOICES = [
        ('ADMISSION_FORM', 'Admission Form / Agreement'),
        ('STUDENT_PORTAL', 'Self-service Portal / App'),
        ('STAFF_ENTRY', 'Staff Administrative Entry'),
        ('INBOUND_MSG', 'Inbound WhatsApp Message (Opt-in)'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='whatsapp_preference'
    )
    whatsapp_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        help_text="E.164 formatted WhatsApp number (e.g. +919876543210)"
    )
    is_whatsapp_verified = models.BooleanField(default=False)
    opt_in_transactional = models.BooleanField(
        default=True,
        help_text="Consent for academic, fee, and operational alerts"
    )
    opt_in_marketing = models.BooleanField(
        default=False,
        help_text="Consent for promotional workshops, courses, and offers"
    )
    consent_source = models.CharField(
        max_length=30,
        choices=CONSENT_SOURCE_CHOICES,
        default='ADMISSION_FORM'
    )
    consent_ip_address = models.GenericIPAddressField(null=True, blank=True)

    opted_out_at = models.DateTimeField(null=True, blank=True, db_index=True)
    opt_out_reason = models.CharField(max_length=255, null=True, blank=True)

    @property
    def is_eligible_transactional(self) -> bool:
        return bool(
            self.whatsapp_phone and
            self.opt_in_transactional and
            self.opted_out_at is None
        )

    def __str__(self):
        return f"WhatsApp prefs for {self.user_id}"


class WhatsAppTemplate(BaseModel):
    """Registry of pre-approved Meta WhatsApp message templates."""

    CATEGORY_CHOICES = [
        ('UTILITY', 'Utility (Class alerts, fees, attendance)'),
        ('MARKETING', 'Marketing (Promotions, new courses)'),
        ('AUTHENTICATION', 'Authentication (OTPs, password resets)'),
    ]

    HEADER_TYPE_CHOICES = [
        ('NONE', 'None'),
        ('TEXT', 'Text Header'),
        ('DOCUMENT', 'PDF Document (Receipts, Reports)'),
        ('IMAGE', 'Image (Schedules, Notices)'),
    ]

    template_key = models.CharField(max_length=60, unique=True, db_index=True)
    meta_template_name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='UTILITY')
    language_code = models.CharField(max_length=10, default='en_US')
    header_type = models.CharField(max_length=20, choices=HEADER_TYPE_CHOICES, default='NONE')
    body_text_sample = models.TextField(blank=True, default='')
    parameter_schema = models.JSONField(default=list)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return f"{self.template_key} -> {self.meta_template_name}"


class WhatsAppDelivery(BaseModel):
    """Per-recipient WhatsApp dispatch state, provider IDs, and audit log."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending Enqueue'),
        ('QUEUED', 'Queued in Worker'),
        ('SUBMITTED', 'Submitted to Meta'),
        ('SENT', 'Sent (Carrier Accepted)'),
        ('DELIVERED', 'Delivered to Handset'),
        ('READ', 'Read by Recipient'),
        ('FAILED', 'Delivery Failed'),
        ('SKIPPED', 'Skipped (No number / No consent / Opted out)'),
        ('OPTED_OUT', 'Suppressed (User previously opted out)'),
    ]

    RECIPIENT_ROLE_CHOICES = [
        ('STUDENT', 'Student'),
        ('PARENT', 'Parent'),
        ('STAFF', 'Staff'),
    ]

    notification = models.ForeignKey(
        'communications.Notification',
        on_delete=models.CASCADE,
        related_name='whatsapp_deliveries'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='whatsapp_receipts'
    )
    recipient_role = models.CharField(max_length=20, choices=RECIPIENT_ROLE_CHOICES, default='STUDENT')
    phone_snapshot = models.CharField(max_length=20, blank=True, default='')
    template = models.ForeignKey(
        WhatsAppTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    template_name = models.CharField(max_length=120)
    template_parameters = models.JSONField(default=dict)
    header_media_url = models.URLField(max_length=500, blank=True, null=True)

    provider = models.CharField(max_length=30, default='META_CLOUD')
    provider_message_id = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)

    error_code = models.CharField(max_length=50, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)

    pricing_category = models.CharField(max_length=30, blank=True, null=True)
    estimated_cost = models.DecimalField(max_digits=6, decimal_places=4, default=0.0000)

    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at'], name='wa_delivery_status_idx'),
            models.Index(fields=['recipient', 'status'], name='wa_delivery_recip_status_idx'),
        ]

    def __str__(self):
        return f"WhatsAppDelivery {self.id} -> {self.recipient_id} [{self.status}]"


class DeviceToken(BaseModel):
    """A push-notification handle for one physical install of the mobile app.

    ``expo_push_token`` is unique across the whole table rather than per user on
    purpose: a handset that is signed out and handed to the next user would
    otherwise keep delivering the previous user's alerts. Re-registering the same
    token reassigns it, which is what a shared-device kiosk install needs.
    """

    PLATFORM_CHOICES = [
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens',
    )
    expo_push_token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='android')
    device_name = models.CharField(max_length=120, blank=True, null=True)
    app_version = models.CharField(max_length=32, blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active'], name='devicetoken_user_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} on {self.platform} ({self.expo_push_token[:12]}...)"
