"""Shared authorizer execution service.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

from .allow_all import AllowAllAuthorizer
from .base import Authorizer, AuthorizerInput
from .source_subnet import SourceSubnetAuthorizer
from ..config import AppConfig
from ..errors import AuthorizationError


class AuthorizerService:
    """Builds and evaluates configured authorizers in one place."""

    def __init__(self, config: AppConfig) -> None:
        registry: dict[str, Authorizer] = {}
        for item in config.authorizers:
            if item.type == "source_subnet":
                registry[item.name] = SourceSubnetAuthorizer(
                    name=item.name,
                    source_subnets=item.source_subnets or [],
                )
            elif item.type == "allow_all":
                registry[item.name] = AllowAllAuthorizer(name=item.name)
            else:
                raise AuthorizationError(f"unsupported authorizer type: {item.type}")
        self._registry = registry

    def allowed_authorizers(self, request: AuthorizerInput) -> set[str]:
        """Allowed authorizers for AuthorizerService.

        Args:
            request: Normalized request input for authorizer/proof evaluation.

        Returns:
            Set of matched values.
        """
        allowed: set[str] = set()
        for name, authorizer in self._registry.items():
            result = authorizer.evaluate(request)
            if result.allowed:
                allowed.add(name)
        return allowed

    def require_authorizers(self, names: list[str], request: AuthorizerInput) -> set[str]:
        """Require authorizers for AuthorizerService.

        Args:
            names: Required authorizer names that must permit the request.
            request: Normalized request input for authorizer/proof evaluation.

        Returns:
            Set of matched values.
        """
        allowed: set[str] = set()
        for name in names:
            authorizer = self._registry.get(name)
            if authorizer is None:
                raise AuthorizationError(f"unknown authorizer: {name}")
            result = authorizer.evaluate(request)
            if not result.allowed:
                raise AuthorizationError(result.reason)
            allowed.add(result.authorizer_name)
        return allowed
