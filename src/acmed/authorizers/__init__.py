"""Authorizer plugin registry.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

from .allow_all import AllowAllAuthorizer
from .base import Authorizer, AuthorizerInput, AuthorizerResult
from .service import AuthorizerService
from .source_subnet import SourceSubnetAuthorizer

__all__ = [
    "Authorizer",
    "AuthorizerInput",
    "AuthorizerResult",
    "AuthorizerService",
    "AllowAllAuthorizer",
    "SourceSubnetAuthorizer",
]
