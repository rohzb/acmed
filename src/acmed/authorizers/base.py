"""Authorizer plugin contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class AuthorizerInput:
    """Normalized input passed to authorizer plugins."""
    requester_id: str
    request_ip: str | None
    dns_names: list[str]


@dataclass(slots=True)
class AuthorizerResult:
    """Structured result returned by authorizer plugins."""
    authorizer_name: str
    allowed: bool
    reason: str
    evidence: dict[str, str]


class Authorizer(Protocol):
    """Protocol for requester-authorization plugins."""
    name: str

    def evaluate(self, request: AuthorizerInput) -> AuthorizerResult:
        """Evaluate whether requester input is permitted by this authorizer."""
