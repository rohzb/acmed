from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID

from acmed.config import IssuerProfile
from acmed.issuers import IssueRequest
from acmed.issuers.mock import MockIssuerBackend


def test_mock_issuer_returns_parseable_certificate_and_key():
    backend = MockIssuerBackend()
    result = backend.issue(
        profile=IssuerProfile(name="mock", type="mock"),
        request=IssueRequest(
            order_id="order-1",
            dns_names=["host1.lab.example.org", "host2.lab.example.org"],
            common_name="host1.lab.example.org",
            csr_pem=None,
            artifacts_dir="/tmp",
        ),
    )

    assert result.success is True
    assert result.certificate_pem is not None
    assert result.chain_pem is not None
    assert result.fullchain_pem is not None
    assert result.private_key_pem is not None

    cert = x509.load_pem_x509_certificate(result.certificate_pem.encode("utf-8"))
    key = serialization.load_pem_private_key(result.private_key_pem.encode("utf-8"), password=None)

    assert cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == "host1.lab.example.org"
    sans = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "host1.lab.example.org" in sans.get_values_for_type(x509.DNSName)
    assert "host2.lab.example.org" in sans.get_values_for_type(x509.DNSName)
    assert key is not None

    # fullchain must contain at least leaf + issuer cert for certbot compatibility.
    assert result.fullchain_pem.count("BEGIN CERTIFICATE") >= 2
    assert result.chain_pem.count("BEGIN CERTIFICATE") >= 1
