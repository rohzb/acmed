"""Core domain models and enums for acmed."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from hashlib import sha256
from typing import Any


def utc_now() -> datetime:
    """Return current UTC time with timezone information."""
    return datetime.now(timezone.utc)


class OrderStatus(StrEnum):
    """Internal broker lifecycle states for one certificate order."""
    PENDING = "pending"
    AUTHORIZING = "authorizing"
    AUTHORIZED = "authorized"
    ISSUING = "issuing"
    ISSUED = "issued"
    FAILED = "failed"
    DENIED = "denied"
    EXPIRED = "expired"


class CsrSource(StrEnum):
    """How CSR material is supplied for an order."""
    CLIENT_PROVIDED = "client_provided"
    SERVICE_GENERATED = "service_generated"


class PrivateKeyPolicy(StrEnum):
    """How key material is handled for a selected issuance path."""
    SERVICE_GENERATED = "service_generated"
    CSR_ONLY = "csr_only"


TERMINAL_ORDER_STATES = {
    OrderStatus.ISSUED,
    OrderStatus.FAILED,
    OrderStatus.DENIED,
    OrderStatus.EXPIRED,
}


ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.AUTHORIZING, OrderStatus.EXPIRED},
    OrderStatus.AUTHORIZING: {OrderStatus.AUTHORIZED, OrderStatus.DENIED},
    OrderStatus.AUTHORIZED: {OrderStatus.ISSUING, OrderStatus.EXPIRED},
    OrderStatus.ISSUING: {OrderStatus.ISSUED, OrderStatus.FAILED},
    OrderStatus.FAILED: {OrderStatus.PENDING},
    OrderStatus.ISSUED: set(),
    OrderStatus.DENIED: set(),
    OrderStatus.EXPIRED: set(),
}


@dataclass(slots=True)
class OrderRequest:
    """Normalized order creation input used by persistence services."""
    requester_id: str
    requester_ip: str | None
    request_source: str
    dns_names: list[str]
    common_name: str | None = None
    issuer_name: str | None = None
    csr_pem: str | None = None
    idempotency_key: str | None = None
    not_before: datetime | None = None
    not_after: datetime | None = None


@dataclass(slots=True)
class Order:
    """Persisted order row mapped to typed runtime object."""
    id: str
    status: OrderStatus
    requester_id: str
    requester_ip: str | None
    request_source: str
    dns_names: list[str]
    common_name: str | None
    issuer_name: str
    proof_handler_name: str
    challenge_validation_mode: str
    private_key_policy: PrivateKeyPolicy
    csr_source: CsrSource
    not_before: datetime | None
    not_after: datetime | None
    claimed_by: str | None
    claimed_at: datetime | None
    claim_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    retry_count: int
    max_retries: int
    error_message: str | None
    dedupe_key: str


@dataclass(slots=True)
class AuthorizationDecision:
    """Recorded authorization decision metadata."""
    order_id: str
    authorizer_name: str
    decision: str
    reason: str
    evidence: dict[str, Any]
    evaluated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class IssuanceAttempt:
    """Recorded issuer invocation metadata for one attempt."""
    order_id: str
    issuer_name: str
    attempt_number: int
    command: str
    exit_code: int
    stdout_path: str
    stderr_path: str
    started_at: datetime
    finished_at: datetime
    result_code: str


@dataclass(slots=True)
class AuditEvent:
    """Structured audit event entry."""
    id: str
    order_id: str | None
    event_type: str
    actor_type: str
    actor_id: str
    message: str
    metadata: dict[str, Any]
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class AcmeAccount:
    """ACME account record."""
    id: str
    status: str
    jwk_thumbprint: str
    contact: list[str]
    orders_url: str
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class AcmeAuthorization:
    """ACME authorization record linked to an order identifier."""
    id: str
    order_id: str
    identifier_type: str
    identifier_value: str
    status: str
    expires_at: datetime
    wildcard: bool


@dataclass(slots=True)
class AcmeChallenge:
    """ACME challenge record linked to one authorization."""
    id: str
    authorization_id: str
    challenge_type: str
    token: str
    status: str
    validated_at: datetime | None
    error_code: str | None
    error_detail: str | None


def compute_dedupe_key(
    requester_id: str,
    dns_names: list[str],
    issuer_name: str,
    csr_source: CsrSource,
    private_key_policy: PrivateKeyPolicy,
    challenge_validation_mode: str = "strict",
) -> str:
    """Compute server-side dedupe key from normalized fields only."""
    stable_names = sorted(set(dns_names))
    payload = "\n".join(
        [
            requester_id,
            ",".join(stable_names),
            issuer_name,
            csr_source,
            private_key_policy,
            challenge_validation_mode,
        ]
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def new_order_expiry(ttl_seconds: int) -> datetime:
    """Compute order expiration timestamp from TTL seconds."""
    return utc_now() + timedelta(seconds=ttl_seconds)
