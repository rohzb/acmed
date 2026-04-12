"""Audit event helpers.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

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
    """Redact secret-bearing text fragments from audit messages.

    Args:
        value: Raw message content that may contain secrets.

    Returns:
        Sanitized text or `[REDACTED]` when sensitive markers are detected.
    """
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
    """Create a normalized audit event with redacted message content.

    Args:
        order_id: Associated order id, if the event is order-scoped.
        event_type: Stable event type identifier.
        actor_type: Actor category such as `worker` or `service`.
        actor_id: Stable actor identifier.
        message: Human-readable event message.
        metadata: Optional structured metadata payload.

    Returns:
        Ready-to-persist typed audit event record.
    """
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
