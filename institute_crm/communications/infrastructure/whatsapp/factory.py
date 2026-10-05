"""Factory returning the active WhatsApp provider based on settings."""
from __future__ import annotations

from django.conf import settings

from .base import WhatsAppProviderInterface


def get_whatsapp_provider() -> WhatsAppProviderInterface:
    name = (getattr(settings, 'WHATSAPP_PROVIDER', 'MOCK') or 'MOCK').upper()
    if name in ('META', 'META_CLOUD', 'META_CLOUD_API'):
        from .meta_provider import MetaCloudApiProvider

        return MetaCloudApiProvider()
    if name in ('AWS', 'AWS_EUM', 'AWS_SOCIAL'):
        from .aws_provider import AwsSocialMessagingProvider

        return AwsSocialMessagingProvider()
    from .mock_provider import MockWhatsAppProvider

    return MockWhatsAppProvider()
