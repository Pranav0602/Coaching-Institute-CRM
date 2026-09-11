"""
HTTP controller layer for the communications app.
Views validate incoming requests and delegate execution to CommunicationService.
"""
from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from communications.models import Announcement, Notification
from communications.serializers import (
    AnnouncementSerializer,
    NotificationSerializer,
    SendBatchNotificationSerializer,
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
