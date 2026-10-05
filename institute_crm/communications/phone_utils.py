"""E.164 phone normalization and masking helpers for WhatsApp recipients."""
from __future__ import annotations

import phonenumbers


def normalize_phone_number(raw_phone: str | None, default_country: str = 'IN') -> str | None:
    """Return an E.164 formatted number (e.g. '+919876543210') or None if invalid."""
    if not raw_phone:
        return None
    digits = raw_phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    try:
        parsed = phonenumbers.parse(digits, default_country)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def mask_phone_number(phone: str | None) -> str:
    """Mask all but the first 4 and last 2 visible digits for logs/UI."""
    if not phone:
        return ''
    digits = phone.lstrip('+')
    if len(digits) <= 6:
        return '+' + '*' * len(digits)
    return f"+{digits[:4]}{'*' * (len(digits) - 6)}{digits[-2:]}"
