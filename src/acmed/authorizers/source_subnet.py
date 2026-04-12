"""Source subnet authorizer implementation."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address, ip_network

from .base import AuthorizerInput, AuthorizerResult


@dataclass(slots=True)
class SourceSubnetAuthorizer:
    """Authorize requesters by source IP membership in configured subnets."""
    name: str
    source_subnets: list[str]

    def evaluate(self, request: AuthorizerInput) -> AuthorizerResult:
        if request.request_ip is None:
            return AuthorizerResult(
                authorizer_name=self.name,
                allowed=False,
                reason="request_ip required",
                evidence={},
            )

        addr = ip_address(request.request_ip)
        for subnet in self.source_subnets:
            if addr in ip_network(subnet, strict=False):
                return AuthorizerResult(
                    authorizer_name=self.name,
                    allowed=True,
                    reason="request source matched allowed subnet",
                    evidence={"matched_subnet": subnet},
                )

        return AuthorizerResult(
            authorizer_name=self.name,
            allowed=False,
            reason="request source not in allowed subnets",
            evidence={},
        )
