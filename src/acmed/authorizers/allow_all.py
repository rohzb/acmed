"""Authorizer that always permits requests."""

from __future__ import annotations

from dataclasses import dataclass

from .base import AuthorizerInput, AuthorizerResult


@dataclass(slots=True)
class AllowAllAuthorizer:
    """Authorizer implementation that always allows requests."""
    name: str

    def evaluate(self, request: AuthorizerInput) -> AuthorizerResult:
        return AuthorizerResult(
            authorizer_name=self.name,
            allowed=True,
            reason="allow_all authorizer permits request",
            evidence={},
        )
