"""Provider-agnostic boundary for WhatsApp dispatch and webhook parsing."""
from __future__ import annotations

import hmac
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderSendResult:
    ok: bool
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    transient: bool = False
    pricing_category: str | None = None
    estimated_cost: float = 0.0


@dataclass
class WebhookEvent:
    kind: str  # 'status' | 'message'
    provider_message_id: str | None = None
    status: str | None = None  # sent/delivered/read/failed
    timestamp: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    from_phone: str | None = None
    text: str | None = None
    pricing_category: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class WhatsAppProviderInterface(ABC):
    @abstractmethod
    def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        language_code: str,
        parameters: list[dict],
        header_media_url: str | None = None,
        idempotency_key: str | None = None,
    ) -> ProviderSendResult:
        ...

    @abstractmethod
    def send_session_text(
        self,
        to_phone: str,
        text: str,
        idempotency_key: str | None = None,
    ) -> ProviderSendResult:
        ...

    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        ...

    @abstractmethod
    def parse_webhook_payload(self, payload: dict) -> list[WebhookEvent]:
        ...


def verify_meta_signature(raw_body: bytes, signature_header: str, app_secret: str) -> bool:
    """Constant-time HMAC-SHA256 check of Meta's X-Hub-Signature-256."""
    if not signature_header or not signature_header.startswith('sha256='):
        return False
    if not app_secret:
        return False
    expected = hmac.new(app_secret.encode(), msg=raw_body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header[len('sha256='):])
