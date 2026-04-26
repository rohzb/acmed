from __future__ import annotations

import subprocess
from dataclasses import dataclass

from acmed.config import IssuerProfile
from acmed.issuers import subprocess_backend as subprocess_backend_module
from acmed.issuers.subprocess_backend import SubprocessIssuerMixin


@dataclass(slots=True)
class _Harness(SubprocessIssuerMixin):
    """Minimal harness to exercise mixin behavior in isolation."""


def test_run_timeout_coerces_bytes_to_text(monkeypatch):
    harness = _Harness()
    profile = IssuerProfile(name="le", type="acme_sh", timeout_seconds=7)

    def _raise_timeout(*args, **kwargs):  # noqa: ANN002, ANN003
        raise subprocess.TimeoutExpired(cmd=["acme.sh"], timeout=7, output=b"stdout-bytes", stderr=b"stderr-bytes")

    monkeypatch.setattr(subprocess_backend_module.subprocess, "run", _raise_timeout)

    result = harness._run(argv=["acme.sh", "--issue"], profile=profile, cwd=".")

    assert result.exit_code == 124
    assert result.stdout == "stdout-bytes"
    assert "timeout after 7s" in result.stderr
    assert "stderr-bytes" in result.stderr
