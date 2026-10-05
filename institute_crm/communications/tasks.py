"""Celery tasks for WhatsApp delivery dispatch."""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from communications.infrastructure.whatsapp.factory import get_whatsapp_provider
from communications.models import WhatsAppDelivery

logger = logging.getLogger('institute_crm.communications')

MAX_RETRIES = 3
RETRY_COUNTDOWNS = [30, 120, 600]


def _normalize_template_parameters(raw) -> list[dict]:
    """Accept {'1': 'x', '2': 'y'}, ['x', 'y'], or [{'name','text'}] and return [{'name','text'}]."""
    if not raw:
        return []
    if isinstance(raw, dict):
        ordered = sorted(raw.items(), key=lambda kv: str(kv[0]))
        return [{'name': str(k), 'text': str(v)} for k, v in ordered]
    if isinstance(raw, (list, tuple)):
        out = []
        for i, item in enumerate(raw, start=1):
            if isinstance(item, dict):
                out.append({'name': str(item.get('name', i)), 'text': str(item.get('text', ''))})
            else:
                out.append({'name': str(i), 'text': str(item)})
        return out
    return []


@shared_task(bind=True, max_retries=MAX_RETRIES, rate_limit='40/s')
def dispatch_whatsapp_delivery_task(self, delivery_id: str):
    try:
        delivery = (
            WhatsAppDelivery.objects
            .filter(is_deleted=False)
            .select_related('recipient', 'recipient__whatsapp_preference', 'template')
            .get(id=delivery_id)
        )
    except WhatsAppDelivery.DoesNotExist:
        logger.error('WhatsAppDelivery %s not found', delivery_id)
        return

    if delivery.status in ('SENT', 'DELIVERED', 'READ', 'SUBMITTED') and delivery.provider_message_id:
        # Already dispatched (e.g. duplicate enqueue); never double-send.
        logger.info('Delivery %s already %s; skipping', delivery_id, delivery.status)
        return

    prefs = getattr(delivery.recipient, 'whatsapp_preference', None)
    if prefs is None or not prefs.whatsapp_phone:
        delivery.status = 'SKIPPED'
        delivery.error_message = 'No WhatsApp number on file'
        delivery.save(update_fields=['status', 'error_message', 'updated_at', 'version'])
        return
    if not prefs.is_eligible_transactional:
        delivery.status = 'OPTED_OUT' if prefs.opted_out_at else 'SKIPPED'
        delivery.error_message = 'Recipient opted out or consent revoked'
        delivery.save(update_fields=['status', 'error_message', 'updated_at', 'version'])
        return

    delivery.status = 'QUEUED'
    delivery.attempt_count = (delivery.attempt_count or 0) + 1
    delivery.save(update_fields=['status', 'attempt_count', 'updated_at', 'version'])

    params = _normalize_template_parameters(delivery.template_parameters)
    provider = get_whatsapp_provider()
    result = provider.send_template_message(
        to_phone=prefs.whatsapp_phone,
        template_name=delivery.template_name,
        language_code=delivery.template.language_code if delivery.template else 'en_US',
        parameters=params,
        header_media_url=delivery.header_media_url or None,
        idempotency_key=str(delivery.idempotency_key),
    )

    now = timezone.now()
    if result.ok:
        delivery.status = 'SUBMITTED'
        delivery.provider_message_id = result.provider_message_id
        delivery.sent_at = now
        delivery.error_code = None
        delivery.error_message = None
        delivery.pricing_category = result.pricing_category
        delivery.save()
        logger.info('Delivery %s submitted: %s', delivery_id, result.provider_message_id)
        return

    delivery.error_code = result.error_code
    delivery.error_message = result.error_message
    if result.transient and delivery.attempt_count <= MAX_RETRIES:
        countdown = RETRY_COUNTDOWNS[min(delivery.attempt_count - 1, len(RETRY_COUNTDOWNS) - 1)]
        delivery.save()
        logger.warning('Delivery %s transient failure %s; retry in %ss', delivery_id, result.error_code, countdown)
        raise self.retry(countdown=countdown, exc=RuntimeError(result.error_message or 'transient failure'))

    delivery.status = 'FAILED'
    delivery.failed_at = now
    delivery.save()
    logger.error('Delivery %s failed permanently: %s %s', delivery_id, result.error_code, result.error_message)
