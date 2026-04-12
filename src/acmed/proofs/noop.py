"""No-proof handler implementation.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import ProofInput, ProofResult


@dataclass(slots=True)
class NoProofHandler:
    """Proof handler that unconditionally passes proof checks."""

    name: str

    def evaluate(self, request: ProofInput) -> ProofResult:
        """Return a successful no-op proof evaluation result.

        Args:
            request: Proof evaluation input payload.

        Returns:
            Successful proof result with no additional evidence.
        """

        return ProofResult(
            proof_handler_name=self.name,
            passed=True,
            reason="no-proof path configured",
            evidence={},
        )
