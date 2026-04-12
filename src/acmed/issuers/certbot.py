"""Certbot issuer backend wrapper.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass

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

        argv = [
            profile.executable or "certbot",
            "certonly",
            "--non-interactive",
            "--agree-tos",
            "--server",
            profile.ca_directory_url or "",
        ]
        if profile.plugin_name:
            argv.append(f"--{profile.plugin_name}")
        for dns_name in request.dns_names:
            argv.extend(["-d", dns_name])
        return self._issue_by_subprocess(argv=argv, profile=profile, request=request)
