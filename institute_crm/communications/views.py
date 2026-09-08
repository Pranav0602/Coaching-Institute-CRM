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
from communications.serializers import AnnouncementSerializer, NotificationSerializer
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
