"""Issuer adapter contract for certificate backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..config import IssuerProfile


@dataclass(slots=True)
class IssueRequest:
    """Input payload for one backend issuance attempt.

    Attributes:
        order_id: Internal order identifier for traceability.
        dns_names: Subject alternative names requested for the certificate.
        common_name: Optional common name when one is explicitly selected.
        csr_pem: Optional CSR PEM supplied by caller; `None` for service-generated flows.
        artifacts_dir: Working directory for backend outputs and logs.
    """

    order_id: str
    dns_names: list[str]
    common_name: str | None
    csr_pem: str | None
    artifacts_dir: str


@dataclass(slots=True)
class IssueResult:
    """Normalized backend result consumed by worker and storage layers.

    Attributes:
        success: Whether issuance completed successfully.
        result_code: Stable backend outcome code.
        command: Human-readable command line used for issuance.
        exit_code: Backend process exit code.
        stdout: Captured standard output.
        stderr: Captured standard error.
        certificate_pem: Issued leaf certificate PEM, when available.
        chain_pem: Intermediate chain PEM, when available.
        fullchain_pem: Combined leaf+chain PEM, when available.
        private_key_pem: Private key PEM, when backend generated it.
    """

    success: bool
    result_code: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    certificate_pem: str | None = None
    chain_pem: str | None = None
    fullchain_pem: str | None = None
    private_key_pem: str | None = None


class IssuerBackend(Protocol):
    """Plugin interface for certificate issuance backends."""

    name: str

    def issue(self, profile: IssuerProfile, request: IssueRequest) -> IssueResult:
        """Perform issuance for one order with one selected issuer profile.

        Args:
            profile: Issuer profile from YAML configuration.
            request: Runtime issuance request payload.

        Returns:
            Normalized issuance result for storage and audit handling.
        """
