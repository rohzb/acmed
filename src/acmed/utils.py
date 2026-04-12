"""Utility helpers shared across acmed modules.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .errors import ValidationError

_DNS_RE = re.compile(r"^(?:\*\.)?(?=.{1,253}$)(?!-)[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.?$")


def utc_iso(dt: datetime | None) -> str | None:
    """Convert datetime to UTC ISO-8601 text.

    Args:
        dt: Datetime value to convert.

    Returns:
        UTC-normalized ISO-8601 string, or `None` when input is `None`.
    """

    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat()


def normalize_dns_name(name: str) -> str:
    """Normalize and validate one DNS identifier.

    Args:
        name: DNS identifier to normalize.

    Returns:
        Lowercase normalized ASCII form, preserving wildcard prefix when present.

    Raises:
        ValidationError: If the name is empty or violates DNS naming rules.
    """

    candidate = name.strip().rstrip(".").lower()
    if not candidate:
        raise ValidationError("empty dns name")
    if not _DNS_RE.fullmatch(candidate):
        raise ValidationError(f"invalid dns name: {name}")

    wildcard = candidate.startswith("*.")
    bare = candidate[2:] if wildcard else candidate
    labels = bare.split(".")
    if len(labels) < 2:
        raise ValidationError(f"dns name must include at least one dot: {name}")
    for label in labels:
        if not label or len(label) > 63 or label.startswith("-") or label.endswith("-"):
            raise ValidationError(f"invalid dns label in: {name}")
    return candidate.encode("idna").decode("ascii")


def normalize_dns_names(values: list[str]) -> list[str]:
    """Normalize multiple DNS identifiers and reject duplicates.

    Args:
        values: Raw DNS names from request input.

    Returns:
        Normalized DNS names preserving input order.

    Raises:
        ValidationError: If any value is invalid or duplicates exist.
    """

    normalized = [normalize_dns_name(value) for value in values]
    if len(set(normalized)) != len(normalized):
        raise ValidationError("duplicate dns identifiers are not allowed")
    return normalized


def sanitize_text(value: str) -> str:
    """Limit and flatten text for safe storage/logging.

    Args:
        value: Raw text value to sanitize.

    Returns:
        Single-line text truncated to a bounded length.
    """

    return value.replace("\n", " ").replace("\r", " ")[:5000]
