"""acme.sh issuer backend wrapper.

The worker calls this adapter for service-generated keys or client-provided
RSA/EC CSRs. Certificate installation selects the corresponding acme.sh lineage;
client-CSR results are checked against both returned certificate artifacts so
cached certificates for another key cannot be reported as successful issuance.

Author: Ruslan Ovsyannikov
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from ..config import IssuerProfile
from .base import IssueRequest, IssueResult
from .client_certificates import cache_path, read_cached, write_cached
from .subprocess_backend import SubprocessIssuerMixin, SubprocessResult


@dataclass(slots=True)
class AcmeShIssuerBackend(SubprocessIssuerMixin):
    """Issuer backend that shells out to `acme.sh`."""

    name: str = "acme_sh"

    _FORCE_RENEW_HINT: str = "Add '--force' to force to renew."
    _DEFAULT_ACMESH_HOME: str = "/app/data/acmesh"

    def _pem_pair_matches(self, certificate_pem: str | None, private_key_pem: str | None) -> bool:
        """Return whether certificate and private key PEM payloads form a pair."""
        if not certificate_pem or not private_key_pem:
            return False
        try:
            cert = x509.load_pem_x509_certificate(certificate_pem.encode("utf-8"))
            key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
        except Exception:
            return False
        cert_pub = cert.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        key_pub = key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return cert_pub == key_pub

    def _certificate_matches_csr(
        self, certificate_pem: str | None, csr: x509.CertificateSigningRequest
    ) -> bool:
        """Compare the leaf public key with the finalized client's CSR key."""
        if not certificate_pem:
            return False
        try:
            certificate = x509.load_pem_x509_certificate(certificate_pem.encode("utf-8"))
        except ValueError:
            return False
        return certificate.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        ) == csr.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def issue(self, profile: IssuerProfile, request: IssueRequest) -> IssueResult:
        """Run `acme.sh` using the configured issuer profile.

        Args:
            profile: Issuer profile that defines executable and plugin settings.
            request: Order issuance request.

        Returns:
            Normalized backend result from subprocess execution.
        """

        if profile.challenge_mode and profile.challenge_mode != "dns-01":
            return IssueResult(
                success=False,
                result_code="issuer_error",
                command=profile.executable or "acme.sh",
                exit_code=64,
                stdout="",
                stderr=f"unsupported acme.sh challenge_mode: {profile.challenge_mode}",
            )
        if not profile.plugin_name:
            return IssueResult(
                success=False,
                result_code="issuer_error",
                command=profile.executable or "acme.sh",
                exit_code=64,
                stdout="",
                stderr="acme.sh dns-01 requires non-empty plugin_name",
            )
        if not request.dns_names:
            return IssueResult(
                success=False,
                result_code="issuer_error",
                command=profile.executable or "acme.sh",
                exit_code=64,
                stdout="",
                stderr="acme.sh request requires at least one dns name",
            )

        executable = profile.executable or "acme.sh"
        acmesh_home = os.environ.get("ACMED_ACMESH_HOME", self._DEFAULT_ACMESH_HOME)
        use_signcsr = request.csr_pem is not None
        csr: x509.CertificateSigningRequest | None = None
        use_ecc = not use_signcsr
        if request.csr_pem is not None:
            try:
                csr = x509.load_pem_x509_csr(request.csr_pem.encode("utf-8"))
                if not csr.is_signature_valid:
                    raise ValueError("client CSR signature is invalid")
                public_key = csr.public_key()
                if not isinstance(public_key, (rsa.RSAPublicKey, ec.EllipticCurvePublicKey)):
                    raise ValueError("acme.sh requires an RSA or EC CSR public key")
                use_ecc = isinstance(public_key, ec.EllipticCurvePublicKey)
            except ValueError as error:
                return IssueResult(
                    success=False,
                    result_code="issuer_error",
                    command=executable,
                    exit_code=64,
                    stdout="",
                    stderr=f"invalid or unsupported client CSR: {error}",
                )
        client_cache: Path | None = None
        if csr is not None and profile.reuse_client_certificates:
            client_cache = cache_path(acmesh_home, profile, request)
            if not profile.force_renew:
                cached = read_cached(client_cache, request)
                if cached is not None:
                    return cached
        issue_argv = [
            executable,
            "--signcsr" if use_signcsr else "--issue",
            "--home",
            acmesh_home,
            "--server",
            profile.ca_directory_url or "",
            "--dns",
            profile.plugin_name,
        ]
        csr_path: Path | None = None
        if use_signcsr:
            fd, raw_path = tempfile.mkstemp(prefix="acmed-", suffix=".csr", dir=request.artifacts_dir)
            csr_path = Path(raw_path)
            os.close(fd)
            csr_path.write_text(request.csr_pem or "", encoding="utf-8")
            issue_argv.extend(["--csr", str(csr_path)])
        if not use_signcsr:
            issue_argv.extend(["--keylength", "ec-256"])
        # A cache miss must fulfill this CSR rather than reuse another lineage key.
        if profile.force_renew or (csr is not None and profile.reuse_client_certificates):
            issue_argv.append("--force")
        for dns_name in request.dns_names:
            issue_argv.extend(["-d", dns_name])

        issue_result = self._run(argv=issue_argv, profile=profile, cwd=request.artifacts_dir)
        if csr_path is not None:
            csr_path.unlink(missing_ok=True)
        can_reuse_existing = (not profile.force_renew) and self._is_existing_cert_reuse_hint(issue_result)
        if issue_result.exit_code != 0 and not can_reuse_existing:
            return IssueResult(
                success=False,
                result_code="issuer_error",
                command=" ".join(issue_result.command),
                exit_code=issue_result.exit_code,
                stdout=issue_result.stdout,
                stderr=issue_result.stderr,
            )

        primary_domain = request.common_name or request.dns_names[0]
        cert_path = Path(request.artifacts_dir) / "certificate.pem"
        chain_path = Path(request.artifacts_dir) / "chain.pem"
        fullchain_path = Path(request.artifacts_dir) / "fullchain.pem"
        key_path = Path(request.artifacts_dir) / "private.key"
        install_argv = [
            executable,
            "--install-cert",
            "--home",
            acmesh_home,
            "-d",
            primary_domain,
            "--cert-file",
            str(cert_path),
            "--ca-file",
            str(chain_path),
            "--fullchain-file",
            str(fullchain_path),
        ]
        if request.csr_pem is None:
            install_argv.extend(
                [
                    "--key-file",
                    str(key_path),
                ]
            )
        if use_ecc:
            install_argv.append("--ecc")
        install_result = self._run(argv=install_argv, profile=profile, cwd=request.artifacts_dir)

        command = " && ".join([" ".join(issue_result.command), " ".join(install_result.command)])
        stdout = "\n".join(part for part in [issue_result.stdout, install_result.stdout] if part)
        stderr = "\n".join(part for part in [issue_result.stderr, install_result.stderr] if part)
        cert = self._read_if_exists(cert_path)
        chain = self._read_if_exists(chain_path)
        fullchain = self._read_if_exists(fullchain_path)
        key = self._read_if_exists(key_path)
        if fullchain is None and cert is not None:
            # Some acme.sh runs emit cert+chain but skip fullchain file.
            fullchain = f"{cert}{chain or ''}"
            fullchain_path.write_text(fullchain, encoding="utf-8")
        missing = []
        if cert is None:
            missing.append("certificate.pem")
        if fullchain is None:
            missing.append("fullchain.pem")
        if request.csr_pem is None and key is None:
            missing.append("private.key")
        if missing:
            return IssueResult(
                success=False,
                result_code="issuer_error",
                command=command,
                exit_code=65,
                stdout=stdout,
                stderr="\n".join(
                    part for part in [stderr, f"issuer output missing required artifacts: {', '.join(missing)}"] if part
                ),
                certificate_pem=cert,
                chain_pem=chain,
                fullchain_pem=fullchain,
                private_key_pem=key,
            )

        if csr is not None and not all(
            self._certificate_matches_csr(pem, csr) for pem in (cert, fullchain)
        ):
            return IssueResult(
                success=False,
                result_code="issuer_error",
                command=command,
                exit_code=66,
                stdout=stdout,
                stderr="\n".join(
                    part for part in [stderr, "acme.sh certificate does not match client CSR public key"]
                    if part
                ),
            )

        if request.csr_pem is None and not self._pem_pair_matches(cert, key):
            return IssueResult(
                success=False,
                result_code="issuer_error",
                command=command,
                exit_code=66,
                stdout=stdout,
                stderr="\n".join(
                    part
                    for part in [stderr, "acme.sh install output produced mismatched certificate/private key pair"]
                    if part
                ),
                certificate_pem=cert,
                chain_pem=chain,
                fullchain_pem=fullchain,
                private_key_pem=key,
            )

        result = IssueResult(
            success=install_result.exit_code == 0,
            result_code="issued" if install_result.exit_code == 0 else "issuer_error",
            command=command,
            exit_code=install_result.exit_code,
            stdout=stdout,
            stderr=stderr,
            certificate_pem=cert,
            chain_pem=chain,
            fullchain_pem=fullchain,
            private_key_pem=key,
        )
        if result.success and client_cache is not None:
            try:
                write_cached(client_cache, result)
            except OSError:
                result.stderr += "\nClient-certificate cache could not be written."
        return result

    def _is_existing_cert_reuse_hint(self, result: SubprocessResult) -> bool:
        """Return whether acme.sh asks to reuse existing cert state.

        Args:
            result: Captured result of `acme.sh --issue`.

        Returns:
            `True` when acme.sh indicates an existing cert can be reused without
            forcing renewal.
        """

        if result.exit_code != 2:
            return False
        return self._FORCE_RENEW_HINT in f"{result.stdout}\n{result.stderr}"
