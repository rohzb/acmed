"""Audit event helpers."""

from __future__ import annotations

import uuid
from typing import Any

from .models import AuditEvent
from .utils import sanitize_text


SENSITIVE_MARKERS = [
    "private key",
    "aws_secret_access_key",
    "cf_token",
    "authorization:",
    "eab",
]


def redact_sensitive(value: str) -> str:
    """Redact secret-bearing text fragments from audit messages."""
    text = sanitize_text(value)
    lowered = text.lower()
    for marker in SENSITIVE_MARKERS:
        if marker in lowered:
            return "[REDACTED]"
    return text


def make_audit_event(
    order_id: str | None,
    event_type: str,
    actor_type: str,
    actor_id: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Create normalized audit event with redacted message content."""
    safe_metadata = metadata or {}
    return AuditEvent(
        id=str(uuid.uuid4()),
        order_id=order_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        message=redact_sensitive(message),
        metadata=safe_metadata,
    )
