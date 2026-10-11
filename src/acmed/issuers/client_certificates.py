"""Persist public client-certificate results for repeat requests with the same key.

The acme.sh adapter uses this cache after normal broker authorization. A cache
identity binds issuer configuration, requested DNS names and the CSR public key;
it never stores client private keys or acts as an authorization credential.

Author: Ruslan Ovsyannikov
License: MIT
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from ..config import IssuerProfile
from .base import IssueRequest, IssueResult


def cache_path(home: str, profile: IssuerProfile, request: IssueRequest) -> Path:
    """Locate public artifacts for an issuer, exact DNS set and client key.

    Args:
        home: Protected issuer state directory.
        profile: Selected issuer configuration.
        request: Authorized client-CSR request.

    Returns:
        Opaque digest path, independent of the ACME order or account ID.

    Raises:
        ValueError: If the supplied CSR cannot be decoded.
    """
    csr = x509.load_pem_x509_csr((request.csr_pem or "").encode())
    settings = asdict(profile)
    for option in ("force_renew", "reuse_client_certificates", "timeout_seconds"):
        settings.pop(option)
    identity = json.dumps({
        "issuer": settings,
        "dns_names": sorted(set(name.lower().rstrip(".") for name in request.dns_names)),
        "public_key": csr.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        ).hex(),
    }, sort_keys=True).encode()
    return Path(home) / "client-certificates" / (hashlib.sha256(identity).hexdigest() + ".json")


def read_cached(path: Path, request: IssueRequest) -> IssueResult | None:
    """Read a matching certificate outside its renewal window, or return a miss.

    Args:
        path: Profile/key-scoped cache entry in trusted broker storage.
        request: Authorized request containing the client's CSR.

    Returns:
        Public issuance result when both leaves match the CSR, exact DNS set and
        validity window; otherwise None. Corrupt cache state is a cache miss.
    """
    try:
        if path.stat().st_size > 1024 * 1024:
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        csr = x509.load_pem_x509_csr((request.csr_pem or "").encode())
        public_key = csr.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        leaves = [x509.load_pem_x509_certificate(record[key].encode())
                  for key in ("certificate_pem", "fullchain_pem")]
        names = {name.lower().rstrip(".") for name in request.dns_names}
        now = datetime.now(timezone.utc)
        for leaf in leaves:
            if leaf.public_key().public_bytes(
                serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
            ) != public_key:
                return None
            sans = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            if len(sans) != len(names) or {
                name.lower().rstrip(".") for name in sans.get_values_for_type(x509.DNSName)
            } != names:
                return None
            if leaf.not_valid_before_utc > now or leaf.not_valid_after_utc <= now + timedelta(days=30):
                return None
        if leaves[0].public_bytes(serialization.Encoding.DER) != leaves[1].public_bytes(
            serialization.Encoding.DER
        ):
            return None
        return IssueResult(
            success=True, result_code="reused", command="client-certificate-cache",
            exit_code=0, stdout="Reused matching public certificate; no upstream request.",
            stderr="", certificate_pem=record["certificate_pem"],
            fullchain_pem=record["fullchain_pem"], chain_pem=record.get("chain_pem"),
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError, x509.ExtensionNotFound):
        return None


def write_cached(path: Path, result: IssueResult) -> None:
    """Atomically retain successful public artifacts, without any private key.

    Args:
        path: Profile/key-scoped destination.
        result: Verified successful client-CSR issuance result.

    Raises:
        OSError: If the protected cache cannot be written.
    """
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    record = {key: getattr(result, key)
              for key in ("certificate_pem", "chain_pem", "fullchain_pem")}
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
