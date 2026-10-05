"""AWS End User Messaging Social provider (boto3 socialmessaging) with graceful fallback."""
from __future__ import annotations

import logging

from django.conf import settings

from .base import ProviderSendResult, WebhookEvent, WhatsAppProviderInterface

logger = logging.getLogger('institute_crm.communications')


class AwsSocialMessagingProvider(WhatsAppProviderInterface):
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3

            self._client = boto3.client(
                'socialmessaging',
                region_name=getattr(settings, 'AWS_REGION', 'ap-south-1'),
                endpoint_url=getattr(settings, 'AWS_ENDPOINT_URL', None) or None,
            )
        return self._client

    def send_template_message(self, to_phone, template_name, language_code, parameters,
                              header_media_url=None, idempotency_key=None) -> ProviderSendResult:
        try:
            client = self._get_client()
            resp = client.send_whatsapp_message(
                originationPhoneNumberId=getattr(settings, 'AWS_WHATSAPP_ORIGINATION_ID', ''),
                destinationPhoneNumber=to_phone,
                templateName=template_name,
                languageCode=language_code,
                templateParameters=[{'name': p.get('name', ''), 'value': str(p.get('text', ''))} for p in parameters],
            )
            return ProviderSendResult(ok=True, provider_message_id=resp.get('messageId'))
        except Exception as exc:  # noqa: BLE001 - provider SDK raises many types
            logger.warning('AWS socialmessaging send failed: %s', exc)
            return ProviderSendResult(ok=False, error_code='aws_error', error_message=str(exc), transient=True)

    def send_session_text(self, to_phone, text, idempotency_key=None) -> ProviderSendResult:
        try:
            client = self._get_client()
            resp = client.send_whatsapp_message(
                originationPhoneNumberId=getattr(settings, 'AWS_WHATSAPP_ORIGINATION_ID', ''),
                destinationPhoneNumber=to_phone,
                text=text,
            )
            return ProviderSendResult(ok=True, provider_message_id=resp.get('messageId'))
        except Exception as exc:  # noqa: BLE001
            logger.warning('AWS socialmessaging text failed: %s', exc)
            return ProviderSendResult(ok=False, error_code='aws_error', error_message=str(exc), transient=True)

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        # AWS EUM delivers via SNS/EventBridge; fall back to Meta-compatible check.
        from .base import verify_meta_signature

        return verify_meta_signature(raw_body, signature_header, settings.WHATSAPP_APP_SECRET)

    def parse_webhook_payload(self, payload: dict) -> list[WebhookEvent]:
        events = []
        for status in payload.get('events', []) or []:
            events.append(WebhookEvent(
                kind='status',
                provider_message_id=status.get('messageId'),
                status=(status.get('eventType') or '').lower(),
                timestamp=status.get('timestamp'),
            ))
        return events
