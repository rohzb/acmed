"""Shared subprocess helpers for acme.sh/certbot backends."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..config import IssuerProfile
from ..errors import WorkerError
from .base import IssueRequest, IssueResult


@dataclass(slots=True)
class SubprocessResult:
    """Raw subprocess execution details before ACMED result normalization."""

    command: list[str]
    exit_code: int
    stdout: str
    stderr: str


class SubprocessIssuerMixin:
    """Shared subprocess execution helper for CLI-based issuer backends."""

    def _filtered_env(self, profile: IssuerProfile) -> dict[str, str]:
        """Build a minimal environment with only required credential variables.

        Args:
            profile: Issuer profile with optional `credential_env` requirements.

        Returns:
            Environment mapping used for backend subprocess invocation.

        Raises:
            WorkerError: If a required credential environment variable is missing.
        """

        env = {"PATH": os.environ.get("PATH", "")}
        for name in profile.credential_env or []:
            value = os.environ.get(name)
            if value is None:
                raise WorkerError(f"missing issuer credential env var: {name}")
            env[name] = value
        return env

    def _run(self, argv: list[str], profile: IssuerProfile, cwd: str) -> SubprocessResult:
        """Execute backend command and return captured output.

        Args:
            argv: Command and arguments to execute.
            profile: Issuer profile defining timeout and credential requirements.
            cwd: Working directory for command execution.

        Returns:
            Captured subprocess result object.
        """

        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                env=self._filtered_env(profile),
                check=False,
                capture_output=True,
                text=True,
                timeout=profile.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return SubprocessResult(argv, exit_code=124, stdout=exc.stdout or "", stderr="timeout")

        return SubprocessResult(
            command=argv,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def _read_if_exists(self, path: Path) -> str | None:
        """Read text from path when present.

        Args:
            path: File path to read.

        Returns:
            UTF-8 file content, or `None` when the file does not exist.
        """

        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def _issue_by_subprocess(self, argv: list[str], profile: IssuerProfile, request: IssueRequest) -> IssueResult:
        """Execute CLI backend and map outputs into `IssueResult`.

        Args:
            argv: Command and arguments to run.
            profile: Issuer profile for timeout and credentials.
            request: Issuance request with artifact working directory.

        Returns:
            Normalized issuance result with optional artifact PEM payloads.
        """

        result = self._run(argv=argv, profile=profile, cwd=request.artifacts_dir)
        cert = self._read_if_exists(Path(request.artifacts_dir) / "certificate.pem")
        chain = self._read_if_exists(Path(request.artifacts_dir) / "chain.pem")
        fullchain = self._read_if_exists(Path(request.artifacts_dir) / "fullchain.pem")
        key = self._read_if_exists(Path(request.artifacts_dir) / "private.key")

        return IssueResult(
            success=result.exit_code == 0,
            result_code="issued" if result.exit_code == 0 else "issuer_error",
            command=" ".join(result.command),
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            certificate_pem=cert,
            chain_pem=chain,
            fullchain_pem=fullchain,
            private_key_pem=key,
        )
