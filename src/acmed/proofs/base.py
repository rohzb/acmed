"""Proof-handler plugin contract.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ProofInput:
    """Input payload for proof-handler plugins.

    Attributes:
        order_id: Internal order identifier.
        requester_id: Requester identity string.
        dns_names: Requested DNS names.
    """

    order_id: str
    requester_id: str
    dns_names: list[str]


@dataclass(slots=True)
class ProofResult:
    """Outcome returned by proof-handler plugins.

    Attributes:
        proof_handler_name: Name of handler producing the result.
        passed: Whether proof requirements were satisfied.
        reason: Human-readable reason for pass/fail.
        evidence: Optional structured evidence captured for audit.
    """

    proof_handler_name: str
    passed: bool
    reason: str
    evidence: dict[str, str]


class ProofHandler(Protocol):
    """Plugin interface for optional pre-issuance proof checks."""

    name: str

    def evaluate(self, request: ProofInput) -> ProofResult:
        """Run optional internal proof checks before issuer invocation.

        Args:
            request: Proof evaluation input payload.

        Returns:
            Proof evaluation result for policy/workflow decisions.
        """
