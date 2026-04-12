"""Inventory-assertion proof handler.

This MVP implementation accepts a static local inventory source marker and records
proof metadata. It intentionally stays minimal and does not connect to external
inventory APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import ProofInput, ProofResult


@dataclass(slots=True)
class InventoryAssertionProofHandler:
    """Proof handler that records acceptance based on static inventory source."""

    name: str
    inventory_source: str

    def evaluate(self, request: ProofInput) -> ProofResult:
        """Evaluate proof using a configured static inventory source marker.

        Args:
            request: Proof evaluation input payload.

        Returns:
            Proof result with evidence indicating the inventory source.
        """

        if not self.inventory_source:
            return ProofResult(
                proof_handler_name=self.name,
                passed=False,
                reason="inventory_source missing",
                evidence={},
            )
        return ProofResult(
            proof_handler_name=self.name,
            passed=True,
            reason="inventory assertion accepted",
            evidence={"inventory_source": self.inventory_source},
        )
