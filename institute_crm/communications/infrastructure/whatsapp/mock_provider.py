"""Mock provider for local development, CI, and E2E testing without Meta credentials."""
from __future__ import annotations

import logging
import re
import uuid

from django.conf import settings

from .base import ProviderSendResult, WebhookEvent, WhatsAppProviderInterface, verify_meta_signature

logger = logging.getLogger('institute_crm.communications')

E164_RE = re.compile(r'^\+\d{7,15}$')


class MockWhatsAppProvider(WhatsAppProviderInterface):
    def send_template_message(self, to_phone, template_name, language_code, parameters,
                              header_media_url=None, idempotency_key=None) -> ProviderSendResult:
        if not E164_RE.match(to_phone or ''):
            return ProviderSendResult(ok=False, error_code='invalid_phone', error_message='Phone not E.164', transient=False)
        message_id = f'wamid.MOCK_{uuid.uuid4().hex[:16]}'
        logger.info('[MOCK WHATSAPP] template=%s to=%s params=%s -> %s', template_name, to_phone, parameters, message_id)
        return ProviderSendResult(ok=True, provider_message_id=message_id)

    def send_session_text(self, to_phone, text, idempotency_key=None) -> ProviderSendResult:
        if not E164_RE.match(to_phone or ''):
            return ProviderSendResult(ok=False, error_code='invalid_phone', error_message='Phone not E.164', transient=False)
        message_id = f'wamid.MOCK_{uuid.uuid4().hex[:16]}'
        logger.info('[MOCK WHATSAPP] text to=%s -> %s', to_phone, message_id)
        return ProviderSendResult(ok=True, provider_message_id=message_id)

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        return verify_meta_signature(raw_body, signature_header, settings.WHATSAPP_APP_SECRET)

    def parse_webhook_payload(self, payload: dict) -> list[WebhookEvent]:
        events = []
        if 'events' in payload:
            for e in payload['events']:
                events.append(WebhookEvent(
                    kind=e.get('kind', 'status'),
                    provider_message_id=e.get('provider_message_id'),
                    status=e.get('status'),
                    error_code=e.get('error_code'),
                    error_message=e.get('error_message'),
                    from_phone=e.get('from_phone'),
                    text=e.get('text'),
                ))
            return events
        from .meta_provider import MetaCloudApiProvider

        return MetaCloudApiProvider().parse_webhook_payload(payload)
