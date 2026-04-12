"""Authorizer that always permits requests.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import AuthorizerInput, AuthorizerResult


@dataclass(slots=True)
class AllowAllAuthorizer:
    """Authorizer implementation that always allows requests."""
    name: str

    def evaluate(self, request: AuthorizerInput) -> AuthorizerResult:
        """Evaluate for AllowAllAuthorizer.

        Args:
            request: Normalized request input for authorizer/proof evaluation.

        Returns:
            Result value matching `AuthorizerResult`.
        """
        return AuthorizerResult(
            authorizer_name=self.name,
            allowed=True,
            reason="allow_all authorizer permits request",
            evidence={},
        )
