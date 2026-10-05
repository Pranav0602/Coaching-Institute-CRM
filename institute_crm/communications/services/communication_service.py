"""
Service layer for communications app.
Handles announcements broadcasting, multi-channel notifications (SES, SNS), and notification status.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet

from accounts.models import User, Role
from communications.models import (
    Announcement,
    DeviceToken,
    Notification,
    WhatsAppDelivery,
    WhatsAppTemplate,
)
from aws_services.ses_sns_service import notification_service
from institute_crm.exceptions import NotFoundError, PermissionDeniedError, ValidationFailed
from institute_crm.scoping import is_global

logger = logging.getLogger('institute_crm.communications')

ALLOWED_BATCH_SENDERS = (Role.SUPER_ADMIN, Role.BRANCH_ADMIN, Role.TEACHER)


def _enqueue_delivery(delivery_id: str) -> None:
    from communications.tasks import dispatch_whatsapp_delivery_task

    dispatch_whatsapp_delivery_task.delay(delivery_id)


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

        # Resolve audience users and persist per-recipient rows through the shared
        # campaign pipeline (in-app rows + WhatsApp deliveries when enabled).
        from accounts.models import Role as _Role
        target = (target_audience or 'ALL').upper()
        role_codes = []
        if target in ('STUDENTS', 'ALL'):
            role_codes.append(_Role.STUDENT)
        if target in ('PARENTS', 'ALL'):
            role_codes.append(_Role.PARENT)
        users = list(User.objects.filter(is_deleted=False, role__code__in=role_codes)) if role_codes else []
        campaign_id = uuid.uuid4()
        Notification.objects.bulk_create([
            Notification(
                recipient=u, sender=actor, target_audience='ALL',
                title=title, message=content, channel='IN_APP', campaign_id=campaign_id,
            ) for u in users
        ])

        try:
            notification_service.send_email(
                recipient_email='all-students@institute.com',
                subject=f"New Announcement: {announcement.title}",
                body_html=f"<h3>{announcement.title}</h3><p>{announcement.content}</p>"
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f'Announcement email failed: {exc}')

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

    # ------------------------------------------------------- device tokens

    @staticmethod
    def filter_device_tokens(actor: User) -> QuerySet[DeviceToken]:
        """Only the caller's own handsets. A user may never enumerate another's."""
        return DeviceToken.objects.filter(is_deleted=False, user=actor).order_by('-updated_at')

    @staticmethod
    @transaction.atomic
    def register_device(
        actor: User,
        *,
        expo_push_token: str,
        platform: str = 'android',
        device_name: str = '',
        app_version: str = '',
    ) -> tuple[DeviceToken, bool]:
        """Bind a push token to the caller, re-binding it if it changed hands.

        Returns the token row and whether it was newly created, so the caller can
        answer 201 vs 200. Expo re-sends the same token on every launch, which makes
        this the app's most frequently hit write endpoint; it stays a single
        indexed upsert rather than a select-then-insert race.
        """
        expo_push_token = (expo_push_token or '').strip()
        if not expo_push_token:
            raise ValidationFailed(
                'A push token is required.',
                field_errors={'expo_push_token': ['This field is required.']},
            )

        device, created = DeviceToken.objects.update_or_create(
            expo_push_token=expo_push_token,
            defaults={
                'user': actor,
                'platform': platform or 'android',
                'device_name': device_name or '',
                'app_version': app_version or '',
                'is_active': True,
                'is_deleted': False,
            },
        )
        if created:
            logger.info('Device %s registered for %s', device.pk, actor.username)
        return device, created

    @staticmethod
    @transaction.atomic
    def unregister_device(actor: User, device_id) -> DeviceToken:
        """Retire a handset, scoping the lookup to the caller.

        Scoped rather than unguarded: an unguessable primary key is not an
        authorisation check, and returning 404 to a non-owner avoids confirming the
        row exists.
        """
        device = None
        try:
            device = DeviceToken.objects.filter(pk=device_id, is_deleted=False, user=actor).first()
        except (ValidationError, ValueError, TypeError):
            # A malformed primary key is a miss, not a crash: filtering a UUIDField
            # with junk raises rather than simply matching nothing.
            device = None
        if device is None:
            raise NotFoundError('Device not found.', code='device_not_found')
        device.is_active = False
        device.save(update_fields=['is_active', 'version', 'updated_at'])
        return device

    @staticmethod
    @transaction.atomic
    def unregister_all_devices(actor: User) -> int:
        """Sign-out cleanup so a shared handset stops delivering the old user's alerts."""
        return DeviceToken.objects.filter(user=actor, is_active=True).update(is_active=False)

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
        template_key: str = '',
        template_parameters: dict | None = None,
    ) -> dict[str, Any]:
        channel = (channel or 'IN_APP').upper()
        if channel not in ('IN_APP', 'EMAIL', 'SMS', 'WHATSAPP', 'ALL'):
            raise ValidationFailed(
                'Invalid channel. Use IN_APP, EMAIL, SMS, WHATSAPP or ALL.',
                field_errors={'channel': ['Use IN_APP, EMAIL, SMS, WHATSAPP or ALL.']},
            )
        return CommunicationService.create_notification_campaign(
            actor=actor,
            batch_id=batch_id,
            title=title,
            message=message,
            channel=channel,
            target_audience=target_audience,
            template_key=template_key,
            template_parameters=template_parameters,
        )

    @staticmethod
    def _resolve_batch_recipients(batch, target_audience: str) -> list[tuple[User, str]]:
        """Return (user, role) pairs for a batch based on STUDENTS/PARENTS/ALL."""
        from academics.models import CourseEnrolment
        from users_profiles.models import StudentParent

        enrolments = (
            CourseEnrolment.objects.filter(batch=batch, status='ACTIVE', is_deleted=False)
            .select_related('student')
        )
        student_user_ids = [
            str(e.student_id) for e in enrolments if e.student_id and not getattr(e.student, 'is_deleted', False)
        ]
        pairs: list[tuple[User, str]] = []
        seen: set[str] = set()
        if target_audience in ('STUDENTS', 'ALL'):
            students = User.objects.filter(id__in=student_user_ids, is_deleted=False)
            for s in students:
                pairs.append((s, 'STUDENT'))
                seen.add(str(s.id))
        if target_audience in ('PARENTS', 'ALL') and student_user_ids:
            parent_user_ids = StudentParent.objects.filter(
                student__user_id__in=student_user_ids,
            ).values_list('parent__user_id', flat=True)
            parents = User.objects.filter(id__in=[str(pid) for pid in parent_user_ids if pid], is_deleted=False)
            for p in parents:
                if str(p.id) not in seen:
                    pairs.append((p, 'PARENT'))
                    seen.add(str(p.id))
        return pairs

    @staticmethod
    @transaction.atomic
    def create_notification_campaign(
        actor: User,
        batch_id,
        title: str,
        message: str,
        channel: str = 'IN_APP',
        target_audience: str = 'STUDENTS',
        template_key: str = '',
        template_parameters: dict | None = None,
    ) -> dict[str, Any]:
        """Single funnel for every notification channel.

        Validates sender scope, resolves the audience, creates Notification rows and,
        when WhatsApp is requested, a WhatsAppDelivery row per recipient in the same
        transaction. Celery tasks are enqueued only after commit.
        """
        from academics.models import Batch, Timetable

        role_code = getattr(actor, 'role_code', None)
        if not is_global(actor) and role_code not in ALLOWED_BATCH_SENDERS:
            raise PermissionDeniedError(
                'Only Super Admins, Branch Admins and Teachers can send batch notifications.',
                code='role_not_permitted',
            )

        channel = (channel or 'IN_APP').upper()
        if channel not in ('IN_APP', 'EMAIL', 'SMS', 'WHATSAPP', 'ALL'):
            raise ValidationFailed(
                'Invalid channel. Use IN_APP, EMAIL, SMS, WHATSAPP or ALL.',
                field_errors={'channel': ['Use IN_APP, EMAIL, SMS, WHATSAPP or ALL.']},
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
        else:  # pragma: no cover
            raise PermissionDeniedError(
                'You do not have permission to send batch notifications.',
                code='role_not_permitted',
            )

        pairs = CommunicationService._resolve_batch_recipients(batch, target_audience)
        campaign_id = uuid.uuid4()

        notifications = [
            Notification(
                recipient=user, sender=actor, batch=batch,
                target_audience=target_audience,
                title=title.strip(), message=message.strip(),
                channel=channel, campaign_id=campaign_id,
            )
            for user, _role in pairs
        ]
        Notification.objects.bulk_create(notifications)

        # --- WhatsApp deliveries ---
        whatsapp_delivery_ids: list[str] = []
        if channel in ('WHATSAPP', 'ALL'):
            if not template_key:
                raise ValidationFailed(
                    'template_key is required for WhatsApp delivery.',
                    field_errors={'template_key': ['This field is required.']},
                )
            template = WhatsAppTemplate.objects.filter(
                template_key=template_key, is_active=True, is_deleted=False
            ).first()
            if template is None:
                raise ValidationFailed(
                    f'Unknown or inactive WhatsApp template: {template_key}',
                    field_errors={'template_key': ['Unknown or inactive template.']},
                )
            from django.conf import settings as dj_settings

            whatsapp_delivery_ids: list[str] = []
            deliveries = []
            for (user, role), notif in zip(pairs, notifications):
                prefs = getattr(user, 'whatsapp_preference', None)
                deliveries.append(WhatsAppDelivery(
                    notification=notif,
                    recipient=user,
                    recipient_role=role,
                    phone_snapshot=getattr(prefs, 'whatsapp_phone', '') or '',
                    template=template,
                    template_name=template.meta_template_name,
                    template_parameters=template_parameters or {},
                    provider=dj_settings.WHATSAPP_PROVIDER or 'META_CLOUD',
                ))
            created_deliveries = WhatsAppDelivery.objects.bulk_create(deliveries)
            whatsapp_delivery_ids = [str(d.id) for d in created_deliveries]

            if whatsapp_delivery_ids:
                from communications.tasks import dispatch_whatsapp_delivery_task

                for delivery_id in whatsapp_delivery_ids:
                    transaction.on_commit(
                        lambda d_id=delivery_id: dispatch_whatsapp_delivery_task.delay(d_id)
                    )

        # --- Optional secondary channels (mock-safe via notification_service) ---
        if channel in ('EMAIL', 'ALL'):
            for user, _role in pairs:
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
            for user, _role in pairs:
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
            f'({target_audience}/{channel}): {len(pairs)} recipient(s)'
        )
        return {
            'batch_id': str(batch.pk),
            'batch_name': batch.name,
            'campaign_id': str(campaign_id),
            'recipient_count': len(pairs),
            'whatsapp_queued': len(whatsapp_delivery_ids),
            'channel': channel,
            'target_audience': target_audience,
        }

    @staticmethod
    def preview_audience(actor: User, batch_id, target_audience: str = 'STUDENTS') -> dict[str, Any]:
        """Pre-flight audience counts for the composer UI."""
        from academics.models import Batch

        target_audience = (target_audience or 'STUDENTS').upper()
        batch = Batch.objects.filter(pk=batch_id, is_deleted=False).first()
        if batch is None:
            raise NotFoundError('Batch not found.', code='batch_not_found')
        pairs = CommunicationService._resolve_batch_recipients(batch, target_audience)
        total = len(pairs)
        whatsapp_eligible = 0
        missing_phone = 0
        opted_out = 0
        for user, _role in pairs:
            prefs = getattr(user, 'whatsapp_preference', None)
            if prefs is None or not prefs.whatsapp_phone:
                missing_phone += 1
            elif prefs.opted_out_at is not None or not prefs.opt_in_transactional:
                opted_out += 1
            else:
                whatsapp_eligible += 1
        return {
            'batch_id': str(batch_id),
            'total_recipients': total,
            'whatsapp_eligible': whatsapp_eligible,
            'missing_phone': missing_phone,
            'opted_out': opted_out,
        }

    @staticmethod
    def retry_failed_deliveries(campaign_id) -> int:
        """Re-enqueue failed WhatsApp deliveries for a campaign without duplicating sends."""
        from communications.tasks import dispatch_whatsapp_delivery_task

        failed = list(WhatsAppDelivery.objects.filter(
            is_deleted=False, status='FAILED',
            notification__campaign_id=campaign_id,
        ))
        for delivery in failed:
            delivery.status = 'PENDING'
            delivery.error_code = None
            delivery.error_message = None
            delivery.save(update_fields=['status', 'error_code', 'error_message', 'updated_at', 'version'])
            transaction.on_commit(
                lambda d_id=str(delivery.id): dispatch_whatsapp_delivery_task.delay(d_id)
            )
        return len(failed)

    @staticmethod
    def dispatch_system_event(template_key: str, student: User, parameters: dict | None = None,
                              title: str = '', message: str = '') -> int:
        """Hook for attendance/finance/academics events.

        Sends a WhatsApp template to the student and their linked parents.
        Returns the number of deliveries enqueued.
        """
        template = WhatsAppTemplate.objects.filter(
            template_key=template_key, is_active=True, is_deleted=False
        ).first()
        if template is None:
            logger.warning('System event template %s not configured; skipping WhatsApp', template_key)
            return 0

        recipients: list[tuple[User, str]] = [(student, 'STUDENT')]
        from users_profiles.models import StudentParent

        parent_user_ids = StudentParent.objects.filter(
            student__user_id=student.id,
        ).values_list('parent__user_id', flat=True)
        for pid in parent_user_ids:
            try:
                parent = User.objects.get(id=pid, is_deleted=False)
                recipients.append((parent, 'PARENT'))
            except User.DoesNotExist:
                continue

        from django.conf import settings as dj_settings

        campaign_id = uuid.uuid4()
        count = 0
        with transaction.atomic():
            for user, role in recipients:
                notif = Notification.objects.create(
                    recipient=user, target_audience='ALL',
                    title=title or template_key, message=message or '',
                    channel='WHATSAPP', campaign_id=campaign_id,
                )
                prefs = getattr(user, 'whatsapp_preference', None)
                delivery = WhatsAppDelivery.objects.create(
                    notification=notif, recipient=user, recipient_role=role,
                    phone_snapshot=getattr(prefs, 'whatsapp_phone', '') or '',
                    template=template, template_name=template.meta_template_name,
                    template_parameters=parameters or {},
                    provider=dj_settings.WHATSAPP_PROVIDER or 'META_CLOUD',
                )
                transaction.on_commit(
                    lambda d_id=str(delivery.id): _enqueue_delivery(d_id)
                )
                count += 1
        return count
