"""Certbot issuer backend wrapper.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

from ..config import IssuerProfile
from .base import IssueRequest, IssueResult
from .subprocess_backend import SubprocessIssuerMixin


@dataclass(slots=True)
class CertbotIssuerBackend(SubprocessIssuerMixin):
    """Issuer backend that shells out to `certbot`."""

    name: str = "certbot"

    def issue(self, profile: IssuerProfile, request: IssueRequest) -> IssueResult:
        """Run `certbot certonly` using the configured issuer profile.

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
                command=profile.executable or "certbot",
                exit_code=64,
                stdout="",
                stderr=f"unsupported certbot challenge_mode: {profile.challenge_mode}",
            )
        if not profile.plugin_name:
            return IssueResult(
                success=False,
                result_code="issuer_error",
                command=profile.executable or "certbot",
                exit_code=64,
                stdout="",
                stderr="certbot dns-01 requires non-empty plugin_name",
            )
        if not request.dns_names:
            return IssueResult(
                success=False,
                result_code="issuer_error",
                command=profile.executable or "certbot",
                exit_code=64,
                stdout="",
                stderr="certbot request requires at least one dns name",
            )

        argv = [
            profile.executable or "certbot",
            "certonly",
            "--non-interactive",
            "--agree-tos",
            "--server",
            profile.ca_directory_url or "",
        ]
        cert_path = Path(request.artifacts_dir) / "certificate.pem"
        chain_path = Path(request.artifacts_dir) / "chain.pem"
        fullchain_path = Path(request.artifacts_dir) / "fullchain.pem"
        key_path = Path(request.artifacts_dir) / "private.key"
        argv.extend(["--cert-path", str(cert_path), "--chain-path", str(chain_path), "--fullchain-path", str(fullchain_path)])
        csr_path: Path | None = None
        if request.csr_pem is None:
            argv.extend(["--key-path", str(key_path)])
        else:
            fd, raw_path = tempfile.mkstemp(prefix="acmed-", suffix=".csr", dir=request.artifacts_dir)
            csr_path = Path(raw_path)
            os.close(fd)
            csr_path.write_text(request.csr_pem, encoding="utf-8")
            argv.extend(["--csr", str(csr_path)])
        argv.append(f"--{profile.plugin_name}")
        for dns_name in request.dns_names:
            argv.extend(["-d", dns_name])
        result = self._issue_by_subprocess(argv=argv, profile=profile, request=request)
        if csr_path is not None:
            csr_path.unlink(missing_ok=True)
        if not result.success:
            return result

        missing = []
        if result.certificate_pem is None:
            missing.append("certificate.pem")
        if result.fullchain_pem is None:
            missing.append("fullchain.pem")
        if request.csr_pem is None and result.private_key_pem is None:
            missing.append("private.key")
        if missing:
            result.success = False
            result.result_code = "issuer_error"
            result.exit_code = 65
            result.stderr = "\n".join(
                part
                for part in [result.stderr, f"issuer output missing required artifacts: {', '.join(missing)}"]
                if part
            )
        return result
