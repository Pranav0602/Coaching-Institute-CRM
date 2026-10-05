"""
HTTP controller layer for the communications app.
Views validate incoming requests and delegate execution to CommunicationService.
"""
from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from communications.models import (
    Announcement,
    DeviceToken,
    Notification,
    WhatsAppDelivery,
    WhatsAppPreference,
    WhatsAppTemplate,
)
from communications.serializers import (
    AnnouncementSerializer,
    AudiencePreviewSerializer,
    DeviceRegistrationSerializer,
    DeviceTokenSerializer,
    NotificationSerializer,
    SendBatchNotificationSerializer,
    SendNotificationSerializer,
    WhatsAppDeliverySerializer,
    WhatsAppPreferenceSerializer,
    WhatsAppTemplateSerializer,
)
from communications.services import CommunicationService


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CommunicationService.filter_announcements(self.request.user)

    def perform_create(self, serializer):
        CommunicationService.publish_announcement(
            actor=self.request.user,
            title=serializer.validated_data['title'],
            content=serializer.validated_data['content'],
        )


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        unread_only = self.request.query_params.get('unread') in ['1', 'true', 'True']
        return CommunicationService.filter_notifications(
            self.request.user,
            unread_only=unread_only
        )

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notif = CommunicationService.mark_notification_read(
            actor=request.user,
            notification_id=pk
        )
        return Response({"status": "marked as read", "id": str(notif.id)})

    @action(detail=False, methods=['post'], url_path='send-batch')
    def send_batch(self, request):
        serializer = SendBatchNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = CommunicationService.send_batch_notification(
            actor=request.user,
            batch_id=serializer.validated_data['batch_id'],
            title=serializer.validated_data['title'],
            message=serializer.validated_data['message'],
            channel=serializer.validated_data.get('channel', 'IN_APP'),
            target_audience=serializer.validated_data.get('target_audience', 'STUDENTS'),
            template_key=serializer.validated_data.get('template_key', ''),
            template_parameters=serializer.validated_data.get('template_parameters') or {},
        )
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        return Response({'unread_count': CommunicationService.get_unread_count(request.user)})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        updated = CommunicationService.mark_all_read(request.user)
        return Response({'status': 'all marked as read', 'updated': updated})

    @action(detail=False, methods=['get'], url_path='sent')
    def sent(self, request):
        qs = Notification.objects.filter(
            is_deleted=False, sender=request.user
        ).select_related('batch', 'recipient').order_by('-created_at')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class DeviceTokenViewSet(viewsets.ReadOnlyModelViewSet):
    """``/api/v1/communications/devices/`` - the caller's own push handles.

    Read-only as a collection: tokens are created through ``register`` and retired
    through ``unregister`` so a client can never write fields it has no business
    setting (``is_active``, ``user``).
    """

    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CommunicationService.filter_device_tokens(self.request.user)

    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        serializer = DeviceRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device, created = CommunicationService.register_device(
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(
            DeviceTokenSerializer(device).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post', 'delete'], url_path='unregister')
    def unregister(self, request, pk=None):
        device = CommunicationService.unregister_device(request.user, pk)
        return Response(DeviceTokenSerializer(device).data)

    @action(detail=False, methods=['post'], url_path='unregister-all')
    def unregister_all(self, request):
        retired = CommunicationService.unregister_all_devices(request.user)
        return Response({'retired': retired})

    @action(detail=False, methods=['post'], url_path='send')
    def send(self, request):
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = CommunicationService.create_notification_campaign(
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='preview-audience')
    def preview_audience(self, request):
        serializer = AudiencePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = CommunicationService.preview_audience(
            actor=request.user,
            batch_id=serializer.validated_data['batch_id'],
            target_audience=serializer.validated_data['target_audience'],
        )
        return Response(result)

    @action(detail=False, methods=['get'], url_path='campaign-deliveries')
    def campaign_deliveries(self, request):
        campaign_id = request.query_params.get('campaign_id')
        if not campaign_id:
            return Response({'detail': 'campaign_id query param is required.'}, status=400)
        page = self.paginate_queryset(
            WhatsAppDelivery.objects.filter(is_deleted=False, notification__campaign_id=campaign_id)
            .select_related('recipient').order_by('created_at')
        )
        serializer = WhatsAppDeliverySerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['post'], url_path='retry-failed')
    def retry_failed(self, request):
        campaign_id = request.data.get('campaign_id')
        if not campaign_id:
            return Response({'detail': 'campaign_id is required.'}, status=400)
        count = CommunicationService.retry_failed_deliveries(campaign_id=campaign_id)
        return Response({'requeued': count})


class TemplateListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        templates = WhatsAppTemplate.objects.filter(is_active=True, is_deleted=False).order_by('template_key')
        return Response(WhatsAppTemplateSerializer(templates, many=True).data)


class WhatsAppPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs, _ = WhatsAppPreference.objects.get_or_create(user=request.user)
        return Response(WhatsAppPreferenceSerializer(prefs).data)

    def put(self, request):
        prefs, _ = WhatsAppPreference.objects.get_or_create(user=request.user)
        serializer = WhatsAppPreferenceSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    patch = put
