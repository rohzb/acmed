"""acmed package.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main import AppRuntime


def build_runtime(config_path: str) -> "AppRuntime":
    """Build configured runtime services from a YAML configuration file.

    Args:
        config_path: Path to the acmed YAML configuration file.

    Returns:
        Constructed runtime object with initialized services.
    """
    from .main import build_runtime as _build_runtime

    return _build_runtime(config_path)


def run(config_path: str) -> None:
    """Run the acmed process using the provided YAML configuration file.

    Args:
        config_path: Path to the acmed YAML configuration file.

    Returns:
        `None` after the process exits.
    """
    from .main import run as _run

    _run(config_path)


__all__ = ["build_runtime", "run"]
