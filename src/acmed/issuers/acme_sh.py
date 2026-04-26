"""acme.sh issuer backend wrapper.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import IssuerProfile
from .base import IssueRequest, IssueResult
from .subprocess_backend import SubprocessIssuerMixin


@dataclass(slots=True)
class AcmeShIssuerBackend(SubprocessIssuerMixin):
    """Issuer backend that shells out to `acme.sh`."""

    name: str = "acme_sh"

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
        issue_argv = [
            executable,
            "--issue",
            "--force",
            "--server",
            profile.ca_directory_url or "",
            "--dns",
            profile.plugin_name,
        ]
        for dns_name in request.dns_names:
            issue_argv.extend(["-d", dns_name])

        issue_result = self._run(argv=issue_argv, profile=profile, cwd=request.artifacts_dir)
        if issue_result.exit_code != 0:
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
            "-d",
            primary_domain,
            "--cert-file",
            str(cert_path),
            "--key-file",
            str(key_path),
            "--ca-file",
            str(chain_path),
            "--fullchain-file",
            str(fullchain_path),
        ]
        install_result = self._run(argv=install_argv, profile=profile, cwd=request.artifacts_dir)

        command = " && ".join([" ".join(issue_result.command), " ".join(install_result.command)])
        stdout = "\n".join(part for part in [issue_result.stdout, install_result.stdout] if part)
        stderr = "\n".join(part for part in [issue_result.stderr, install_result.stderr] if part)
        cert = self._read_if_exists(cert_path)
        chain = self._read_if_exists(chain_path)
        fullchain = self._read_if_exists(fullchain_path)
        key = self._read_if_exists(key_path)
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

        return IssueResult(
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
