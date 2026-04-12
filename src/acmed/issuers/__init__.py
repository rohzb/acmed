"""Issuer backend registry and factory.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

from .acme_sh import AcmeShIssuerBackend
from .base import IssuerBackend, IssueRequest, IssueResult
from .certbot import CertbotIssuerBackend
from .mock import MockIssuerBackend


def default_issuer_backends() -> dict[str, IssuerBackend]:
    """Build default issuer backend registry used by the worker.

    Returns:
        Mapping of configured backend `type` names to backend instances.
    """

    return {
        "mock": MockIssuerBackend(),
        "acme_sh": AcmeShIssuerBackend(),
        "certbot": CertbotIssuerBackend(),
    }


__all__ = [
    "IssuerBackend",
    "IssueRequest",
    "IssueResult",
    "default_issuer_backends",
]
