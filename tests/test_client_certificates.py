"""Exercise public-certificate reuse boundaries without external ACME requests."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
import pytest

from acmed.config import ConfigError, IssuerProfile, _load_issuers
from acmed.issuers.base import IssueRequest, IssueResult
from acmed.issuers.acme_sh import AcmeShIssuerBackend
from acmed.issuers.client_certificates import cache_path, read_cached, write_cached
from acmed.issuers.subprocess_backend import SubprocessResult


def _artifacts(days: int = 90, future: bool = False) -> tuple[str, str]:
    """Create a synthetic CSR/certificate pair for bounded reuse tests."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "app.example.org")])
    now = datetime.now(timezone.utc)
    csr = x509.CertificateSigningRequestBuilder().subject_name(subject).sign(key, hashes.SHA256())
    cert = (
        x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now + timedelta(days=1) if future else now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("app.example.org")]), critical=False)
        .sign(key, hashes.SHA256())
    )
    return (csr.public_bytes(serialization.Encoding.PEM).decode(),
            cert.public_bytes(serialization.Encoding.PEM).decode())


@pytest.mark.parametrize("kind", [
    "valid", "near_expiry", "future", "wrong_key", "wrong_san", "bad_json", "wrong_fullchain"
])
def test_cache_validates_lifetime_key_and_names(tmp_path: Path, kind: str) -> None:
    """Accept only usable exact matches; treat damaged state as a miss."""
    csr, cert = _artifacts(20 if kind == "near_expiry" else 90, kind == "future")
    request = IssueRequest("one", ["app.example.org"], None, csr, str(tmp_path))
    profile = IssuerProfile("test", "acme_sh")
    path = cache_path(str(tmp_path), profile, request)
    result = IssueResult(True, "issued", "stub", 0, "", "", cert, "", cert)
    write_cached(path, result)
    if kind == "wrong_key":
        request = replace(request, csr_pem=_artifacts()[0])
    elif kind == "wrong_san":
        request = replace(request, dns_names=["other.example.org"])
    elif kind == "bad_json":
        path.write_text("broken")
    elif kind == "wrong_fullchain":
        write_cached(path, replace(result, fullchain_pem=_artifacts()[1]))
    cached = read_cached(path, request)
    assert (cached is not None) == (kind == "valid")
    assert "private_key" not in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600


def test_cache_identity_is_scoped_to_profile_ca_names_and_key(tmp_path: Path) -> None:
    """Order/account changes do not split reuse, but issuer/key changes do."""
    csr, _ = _artifacts()
    request = IssueRequest("one", ["app.example.org"], None, csr, str(tmp_path))
    profile = IssuerProfile("test", "acme_sh", ca_directory_url="https://ca.example.org")
    path = cache_path(str(tmp_path), profile, request)
    assert path == cache_path(str(tmp_path), profile, replace(request, order_id="two"))
    for changed in (replace(profile, name="other"), replace(profile, ca_directory_url="https://other")):
        assert path != cache_path(str(tmp_path), changed, request)
    assert path != cache_path(str(tmp_path), profile, replace(request, csr_pem=_artifacts()[0]))


def test_repeat_issuance_skips_upstream_but_force_bypasses_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Populate cache on success, reuse matching keys, and honor forced issuance."""
    csr, cert = _artifacts()
    monkeypatch.setenv("ACMED_ACMESH_HOME", str(tmp_path / "home"))
    backend = AcmeShIssuerBackend()
    calls: list[list[str]] = []

    def run(argv: list[str], profile: IssuerProfile, cwd: str) -> SubprocessResult:
        calls.append(argv)
        if "--install-cert" in argv:
            for name in ("certificate.pem", "fullchain.pem"):
                (Path(cwd) / name).write_text(cert)
            (Path(cwd) / "chain.pem").write_text("")
        return SubprocessResult(argv, 0, "ok", "")

    monkeypatch.setattr(backend, "_run", run)
    profile = IssuerProfile("test", "acme_sh", plugin_name="dns_test", reuse_client_certificates=True)
    request = IssueRequest("one", ["app.example.org"], None, csr, str(tmp_path))
    assert backend.issue(profile, request).success
    assert len(calls) == 2
    reused = backend.issue(profile, replace(request, order_id="two"))
    assert reused.success and reused.result_code == "reused"
    assert len(calls) == 2
    assert reused.private_key_pem is None
    assert backend.issue(replace(profile, force_renew=True), request).success
    assert len(calls) == 4 and "--force" in calls[2]


def test_invalid_csr_signature_cannot_use_cached_public_artifacts(tmp_path: Path) -> None:
    """Reject a malformed signature before either cache lookup or subprocess work."""
    csr, _ = _artifacts()
    encoded = bytearray(x509.load_pem_x509_csr(csr.encode()).public_bytes(serialization.Encoding.DER))
    encoded[-1] ^= 1
    invalid = x509.load_der_x509_csr(bytes(encoded)).public_bytes(serialization.Encoding.PEM).decode()
    result = AcmeShIssuerBackend().issue(
        IssuerProfile("test", "acme_sh", plugin_name="dns_test", reuse_client_certificates=True),
        IssueRequest("one", ["app.example.org"], None, invalid, str(tmp_path)),
    )
    assert not result.success and result.exit_code == 64
    assert "invalid" in result.stderr


@pytest.mark.parametrize("issuer_type,value,accepted", [
    ("acme_sh", True, True), ("acme_sh", False, True), ("mock", False, True),
    ("mock", True, False), ("acme_sh", "true", False), ("acme_sh", 1, False),
])
def test_reuse_configuration_is_explicit_and_backend_scoped(
    issuer_type: str, value: object, accepted: bool,
) -> None:
    """Reject ambiguous YAML values and unsupported issuer backends."""
    raw = [{"name": "test", "type": issuer_type, "executable": "/bin/sh",
            "reuse_client_certificates": value}]
    if accepted:
        assert _load_issuers(raw, False)[0].reuse_client_certificates is value
    else:
        with pytest.raises(ConfigError):
            _load_issuers(raw, False)
