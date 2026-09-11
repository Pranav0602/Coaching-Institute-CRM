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
from institute_crm.exceptions import NotFoundError, PermissionDeniedError, ValidationFailed
from institute_crm.scoping import is_global

logger = logging.getLogger('institute_crm.communications')

ALLOWED_BATCH_SENDERS = (Role.SUPER_ADMIN, Role.BRANCH_ADMIN, Role.TEACHER)


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

    @staticmethod
    def get_unread_count(actor: User) -> int:
        return CommunicationService.filter_notifications(actor, unread_only=True).count()

    @staticmethod
    @transaction.atomic
    def mark_all_read(actor: User) -> int:
        return CommunicationService.filter_notifications(actor, unread_only=True).update(is_read=True)

    @staticmethod
    @transaction.atomic
    def send_batch_notification(
        actor: User,
        batch_id,
        title: str,
        message: str,
        channel: str = 'IN_APP',
        target_audience: str = 'STUDENTS',
    ) -> dict[str, Any]:
        from academics.models import Batch, CourseEnrolment, Timetable
        from users_profiles.models import StudentParent

        role_code = getattr(actor, 'role_code', None)
        if not is_global(actor) and role_code not in ALLOWED_BATCH_SENDERS:
            raise PermissionDeniedError(
                'Only Super Admins, Branch Admins and Teachers can send batch notifications.',
                code='role_not_permitted',
            )

        channel = (channel or 'IN_APP').upper()
        if channel not in ('IN_APP', 'EMAIL', 'SMS', 'ALL'):
            raise ValidationFailed(
                'Invalid channel. Use IN_APP, EMAIL, SMS or ALL.',
                field_errors={'channel': ['Use IN_APP, EMAIL, SMS or ALL.']},
            )
        target_audience = (target_audience or 'STUDENTS').upper()
        if target_audience not in ('STUDENTS', 'PARENTS', 'ALL'):
            raise ValidationFailed(
                'Invalid target audience. Use STUDENTS, PARENTS or ALL.',
                field_errors={'target_audience': ['Use STUDENTS, PARENTS or ALL.']},
            )
        if not title or not title.strip():
            raise ValidationFailed('Title is required.', field_errors={'title': ['This field is required.']})
        if not message or not message.strip():
            raise ValidationFailed('Message is required.', field_errors={'message': ['This field is required.']})

        try:
            batch = Batch.objects.select_related('branch', 'course').get(pk=batch_id, is_deleted=False)
        except Batch.DoesNotExist as exc:
            raise NotFoundError('Batch not found.', code='batch_not_found') from exc

        # --- Scoping check ---
        if is_global(actor) or role_code == Role.SUPER_ADMIN:
            pass
        elif role_code == Role.BRANCH_ADMIN:
            if str(batch.branch_id) != str(getattr(actor, 'branch_id', None)):
                raise PermissionDeniedError(
                    'You can only send notifications to batches in your own branch.',
                    code='cross_branch_denied',
                )
        elif role_code == Role.TEACHER:
            teaches = Timetable.objects.filter(
                batch_id=batch.pk, teacher_id=actor.pk, is_deleted=False
            ).exists()
            if not teaches:
                raise PermissionDeniedError(
                    'You can only send notifications to batches you teach.',
                    code='batch_not_taught',
                )
        else:  # pragma: no cover - guarded by role check above
            raise PermissionDeniedError(
                'You do not have permission to send batch notifications.',
                code='role_not_permitted',
            )

        # --- Recipient resolution ---
        enrolments = (
            CourseEnrolment.objects.filter(batch=batch, status='ACTIVE', is_deleted=False)
            .select_related('student')
        )
        student_user_ids = [
            str(e.student_id) for e in enrolments if e.student_id and not getattr(e.student, 'is_deleted', False)
        ]

        recipient_ids: set[str] = set()
        if target_audience in ('STUDENTS', 'ALL'):
            recipient_ids.update(student_user_ids)
        if target_audience in ('PARENTS', 'ALL') and student_user_ids:
            parent_user_ids = StudentParent.objects.filter(
                student__user_id__in=student_user_ids,
            ).values_list('parent__user_id', flat=True)
            recipient_ids.update(str(pid) for pid in parent_user_ids if pid)

        recipients = list(
            User.objects.filter(id__in=list(recipient_ids), is_deleted=False)
        ) if recipient_ids else []

        # --- Dispatch: bulk-create in-app notifications ---
        notifications = [
            Notification(
                recipient=user,
                sender=actor,
                batch=batch,
                target_audience=target_audience,
                title=title.strip(),
                message=message.strip(),
                channel=channel,
            )
            for user in recipients
        ]
        if notifications:
            Notification.objects.bulk_create(notifications)

        # --- Optional secondary channels (mock-safe via notification_service) ---
        if channel in ('EMAIL', 'ALL'):
            for user in recipients:
                email = getattr(user, 'email', None)
                if email:
                    try:
                        notification_service.send_email(
                            recipient_email=email,
                            subject=f'[{batch.name}] {title.strip()}',
                            body_html=f'<h3>{title.strip()}</h3><p>{message.strip()}</p><p><small>Batch: {batch.name}</small></p>',
                        )
                    except Exception as exc:  # noqa: BLE001 - secondary channel must not fail send
                        logger.warning(f'Batch email to {email} failed: {exc}')
        if channel in ('SMS', 'ALL'):
            for user in recipients:
                phone = getattr(user, 'phone', None)
                if phone:
                    try:
                        notification_service.send_sms(
                            phone_number=phone,
                            message=f'[{batch.name}] {title.strip()}: {message.strip()}',
                        )
                    except Exception as exc:  # noqa: BLE001 - secondary channel must not fail send
                        logger.warning(f'Batch SMS to {phone} failed: {exc}')

        logger.info(
            f'Batch notification from user {actor.pk} to batch {batch.pk} '
            f'({target_audience}/{channel}): {len(recipients)} recipient(s)'
        )
        return {
            'batch_id': str(batch.pk),
            'batch_name': batch.name,
            'recipient_count': len(recipients),
            'channel': channel,
            'target_audience': target_audience,
        }
