"""
Service layer for communications app.
Handles announcements broadcasting, multi-channel notifications (SES, SNS), and notification status.
"""
from __future__ import annotations

import logging
from typing import Any
from django.db import transaction
from django.db.models import QuerySet

from accounts.models import User, Role
from communications.models import Announcement, Notification
from aws_services.ses_sns_service import notification_service

logger = logging.getLogger('institute_crm.communications')


class CommunicationService:
    @staticmethod
    def filter_announcements(
        actor: User,
    ) -> QuerySet[Announcement]:
        return Announcement.objects.filter(is_deleted=False).select_related('published_by').order_by('-created_at')

    @staticmethod
    @transaction.atomic
    def publish_announcement(
        actor: User,
        title: str,
        content: str,
        target_audience: str = "ALL",
    ) -> Announcement:
        announcement = Announcement.objects.create(
            title=title,
            content=content,
            published_by=actor,
        )

        # Dispatch via notification service (AWS SES / SNS)
        notification_service.send_email(
            recipient_email="all-students@institute.com",
            subject=f"New Announcement: {announcement.title}",
            body_html=f"<h3>{announcement.title}</h3><p>{announcement.content}</p>"
        )

        logger.info(f"Announcement {announcement.id} '{announcement.title}' published by user {actor.id}")
        return announcement

    @staticmethod
    def filter_notifications(
        actor: User,
        *,
        unread_only: bool = False,
    ) -> QuerySet[Notification]:
        qs = Notification.objects.filter(is_deleted=False, recipient=actor)
        if unread_only:
            qs = qs.filter(is_read=False)
        return qs.order_by('-created_at')

    @staticmethod
    @transaction.atomic
    def mark_notification_read(
        actor: User,
        notification_id: str,
    ) -> Notification:
        notification = Notification.objects.get(id=notification_id, recipient=actor)
        notification.is_read = True
        notification.save()
        return notification
