"""Meta Cloud API provider: direct HTTPS to the Graph API messages endpoint."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

from .base import ProviderSendResult, WebhookEvent, WhatsAppProviderInterface, verify_meta_signature

logger = logging.getLogger('institute_crm.communications')

PERMANENT_ERROR_CODES = {
    '131026',  # message undeliverable
    '131047',
    '132000',  # template does not exist
    '132001',
    '131030',
    '190',     # invalid access token
}
TRANSIENT_STATUS = {429, 500, 502, 503, 504}


class MetaCloudApiProvider(WhatsAppProviderInterface):
    def __init__(self):
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.app_secret = settings.WHATSAPP_APP_SECRET
        self.api_version = settings.WHATSAPP_GRAPH_API_VERSION

    def _endpoint(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"

    def _post(self, payload: dict) -> ProviderSendResult:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            self._endpoint(),
            data=data,
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode('utf-8'))
            messages = body.get('messages') or []
            wamid = messages[0].get('id') if messages else None
            return ProviderSendResult(ok=True, provider_message_id=wamid)
        except urllib.error.HTTPError as exc:
            try:
                payload_err = json.loads(exc.read().decode('utf-8'))
                err = payload_err.get('error', {})
            except Exception:  # noqa: BLE001
                err = {}
            code = str(err.get('code', exc.code))
            transient = exc.code in TRANSIENT_STATUS
            return ProviderSendResult(
                ok=False,
                error_code=code,
                error_message=err.get('message', str(exc)),
                transient=transient,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return ProviderSendResult(ok=False, error_code='network_error', error_message=str(exc), transient=True)

    def send_template_message(self, to_phone, template_name, language_code, parameters,
                              header_media_url=None, idempotency_key=None) -> ProviderSendResult:
        components = []
        if header_media_url:
            components.append({
                'type': 'header',
                'parameters': [{'type': 'document', 'document': {'link': header_media_url}}],
            })
        body_params = [{'type': 'text', 'text': str(p.get('text', ''))} for p in parameters]
        if body_params:
            components.append({'type': 'body', 'parameters': body_params})
        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': to_phone.lstrip('+'),
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {'code': language_code},
                'components': components,
            },
        }
        return self._post(payload)

    def send_session_text(self, to_phone, text, idempotency_key=None) -> ProviderSendResult:
        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': to_phone.lstrip('+'),
            'type': 'text',
            'text': {'body': text},
        }
        return self._post(payload)

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        return verify_meta_signature(raw_body, signature_header, self.app_secret)

    def parse_webhook_payload(self, payload: dict) -> list[WebhookEvent]:
        events: list[WebhookEvent] = []
        for entry in payload.get('entry', []) or []:
            for change in entry.get('changes', []) or []:
                value = change.get('value', {}) or {}
                for status in value.get('statuses', []) or []:
                    first_error = (status.get('errors') or [None])[0] or {}
                    events.append(WebhookEvent(
                        kind='status',
                        provider_message_id=status.get('id'),
                        status=status.get('status'),
                        timestamp=_to_int(status.get('timestamp')),
                        error_code=str(first_error.get('code')) if first_error.get('code') else None,
                        error_message=first_error.get('title') or None,
                        pricing_category=(status.get('conversation') or {}).get('category'),
                    ))
                for msg in value.get('messages', []) or []:
                    text = (msg.get('text') or {}).get('body')
                    events.append(WebhookEvent(
                        kind='message',
                        provider_message_id=msg.get('id'),
                        from_phone=msg.get('from'),
                        text=text,
                        timestamp=_to_int(msg.get('timestamp')),
                    ))
        return events


def _to_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
