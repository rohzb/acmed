"""acme.sh issuer backend wrapper.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass

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

        argv = [
            profile.executable or "acme.sh",
            "--issue",
            "--server",
            profile.ca_directory_url or "",
            "--challenge-alias",
            profile.plugin_name or "",
            "--dns",
            profile.plugin_name or "",
        ]
        for dns_name in request.dns_names:
            argv.extend(["-d", dns_name])
        return self._issue_by_subprocess(argv=argv, profile=profile, request=request)
