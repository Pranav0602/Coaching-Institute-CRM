"""WhatsApp webhook handling: Meta verification handshake + signed event ingest."""
from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.views import View
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status

from communications.infrastructure.whatsapp.base import WebhookEvent
from communications.infrastructure.whatsapp.factory import get_whatsapp_provider
from communications.models import WhatsAppDelivery, WhatsAppPreference
from communications.phone_utils import normalize_phone_number

logger = logging.getLogger('institute_crm.communications')

OPT_OUT_KEYWORDS = {'STOP', 'UNSUBSCRIBE', 'CANCEL'}
OPT_IN_KEYWORDS = {'START', 'UNSTOP'}

# Monotonic rank for lifecycle statuses: a delayed out-of-order callback must never
# downgrade a delivery (e.g. 'sent' arriving after 'read').
_STATUS_RANK = {
    'PENDING': 0,
    'QUEUED': 1,
    'SUBMITTED': 2,
    'SENT': 3,
    'DELIVERED': 4,
    'READ': 5,
    'FAILED': 6,
    'SKIPPED': 6,
    'OPTED_OUT': 6,
}

_META_STATUS_MAP = {
    'sent': 'SENT',
    'delivered': 'DELIVERED',
    'read': 'READ',
    'failed': 'FAILED',
    'submitted': 'SUBMITTED',
    'queued': 'QUEUED',
}


def _apply_status_update(event: WebhookEvent) -> None:
    if event.kind != 'status' or not event.provider_message_id:
        return
    new_status = _META_STATUS_MAP.get((event.status or '').lower(), (event.status or '').upper())
    if not new_status:
        return
    try:
        delivery = WhatsAppDelivery.objects.filter(
            provider_message_id=event.provider_message_id, is_deleted=False
        ).first()
    except Exception:  # noqa: BLE001
        return
    if delivery is None:
        logger.warning('Webhook status for unknown message id %s', event.provider_message_id)
        return

    current_rank = _STATUS_RANK.get(delivery.status, 0)
    new_rank = _STATUS_RANK.get(new_status, 0)
    if new_rank < current_rank and new_status != 'FAILED':
        logger.info('Ignoring out-of-order status %s for delivery %s (current=%s)',
                    new_status, delivery.id, delivery.status)
        return
    if new_status == 'FAILED' and delivery.status == 'READ':
        return

    now = timezone.now()
    delivery.status = new_status
    if new_status == 'SENT':
        delivery.sent_at = delivery.sent_at or now
    elif new_status == 'DELIVERED':
        delivery.delivered_at = delivery.delivered_at or now
    elif new_status == 'READ':
        delivery.read_at = delivery.read_at or now
    elif new_status == 'FAILED':
        delivery.failed_at = now
        delivery.error_code = event.error_code
        delivery.error_message = event.error_message
    if event.pricing_category:
        delivery.pricing_category = event.pricing_category
    delivery.save()
    logger.info('Delivery %s -> %s', delivery.id, new_status)


def _handle_inbound_message(event: WebhookEvent) -> None:
    if event.kind != 'message':
        return
    text = (event.text or '').strip().upper()
    if not text:
        return
    raw_phone = event.from_phone or ''
    phone = normalize_phone_number(raw_phone, default_country='IN') or (
        f'+{raw_phone.lstrip("+")}' if raw_phone else None
    )
    if not phone:
        return
    prefs = WhatsAppPreference.objects.filter(whatsapp_phone=phone).first()
    if prefs is None:
        logger.info('Inbound WhatsApp message from unknown number %s', phone)
        return

    provider = get_whatsapp_provider()
    if text in OPT_OUT_KEYWORDS:
        prefs.opted_out_at = timezone.now()
        prefs.opt_out_reason = 'Inbound STOP keyword'
        prefs.save(update_fields=['opted_out_at', 'opt_out_reason', 'updated_at', 'version'])
        try:
            provider.send_session_text(phone, 'You have unsubscribed from Institute notifications. Reply START at any time to resume.')
        except Exception as exc:  # noqa: BLE001
            logger.warning('STOP confirmation failed: %s', exc)
        return
    if text in OPT_IN_KEYWORDS:
        prefs.opted_out_at = None
        prefs.opt_out_reason = None
        prefs.save(update_fields=['opted_out_at', 'opt_out_reason', 'updated_at', 'version'])
        try:
            provider.send_session_text(phone, 'You have successfully resubscribed to Institute notifications.')
        except Exception as exc:  # noqa: BLE001
            logger.warning('START confirmation failed: %s', exc)
        return
    logger.info('General inbound WhatsApp message from %s: %s', phone, text)


def process_webhook_events(events: list[WebhookEvent]) -> None:
    for event in events:
        if event.kind == 'status':
            _apply_status_update(event)
        elif event.kind == 'message':
            _handle_inbound_message(event)


class WhatsAppWebhookView(View):
    """GET = Meta verification handshake; POST = signed event ingest."""

    def get(self, request):
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if mode == 'subscribe' and token and token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            return HttpResponse(challenge, content_type='text/plain')
        return HttpResponse('Forbidden', status=403)

    def post(self, request):
        provider = get_whatsapp_provider()
        raw_body = request.body
        signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
        if not provider.verify_webhook_signature(raw_body, signature):
            logger.warning('Rejected webhook with invalid signature')
            return HttpResponse('Forbidden', status=403)
        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return HttpResponse('Bad Request', status=400)
        try:
            events = provider.parse_webhook_payload(payload)
            process_webhook_events(events)
        except Exception as exc:  # noqa: BLE001
            logger.exception('Webhook processing failed: %s', exc)
        return HttpResponse('OK', status=200)


class MockWebhookView(View):
    """Local-only endpoint to simulate delivery/read callbacks (DEBUG only)."""

    def post(self, request):
        if not settings.DEBUG:
            return HttpResponse('Not Found', status=404)
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return HttpResponse('Bad Request', status=400)
        provider = get_whatsapp_provider()
        events = provider.parse_webhook_payload(payload)
        process_webhook_events(events)
        return HttpResponse('OK', status=200)
