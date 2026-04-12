"""acmed package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main import AppRuntime


def build_runtime(config_path: str) -> "AppRuntime":
    """Build configured runtime services from YAML configuration path."""
    from .main import build_runtime as _build_runtime

    return _build_runtime(config_path)


def run(config_path: str) -> None:
    """Run ACME service process with worker loop and WSGI server."""
    from .main import run as _run

    _run(config_path)


__all__ = ["build_runtime", "run"]
