"""Mock issuer backend for deterministic tests and local runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from ..config import IssuerProfile
from .base import IssueRequest, IssueResult


@dataclass(slots=True)
class MockIssuerBackend:
    """Deterministic in-process issuer used for tests and local validation."""

    name: str = "mock"

    def issue(self, profile: IssuerProfile, request: IssueRequest) -> IssueResult:
        """Return synthetic certificate artifacts without external dependencies.

        Args:
            profile: Issuer profile from configuration (unused by mock backend).
            request: Order issuance request.

        Returns:
            Successful mock issuance payload with synthetic PEM data.
        """

        dns_names = list(dict.fromkeys(request.dns_names))
        leaf = request.common_name or dns_names[0]

        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        ca_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "acmed-mock-ca")])
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, leaf)])
        now = datetime.now(timezone.utc)

        ca_cert = (
            x509.CertificateBuilder()
            .subject_name(ca_subject)
            .issuer_name(ca_subject)
            .public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .sign(private_key=ca_key, algorithm=hashes.SHA256())
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_subject)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=30))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(name) for name in dns_names]),
                critical=False,
            )
            .sign(private_key=ca_key, algorithm=hashes.SHA256())
        )
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
        chain_pem = ca_cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        return IssueResult(
            success=True,
            result_code="issued",
            command="mock",
            exit_code=0,
            stdout="mock issuer success",
            stderr="",
            certificate_pem=cert_pem,
            chain_pem=chain_pem,
            fullchain_pem=cert_pem + chain_pem,
            private_key_pem=key_pem,
        )
