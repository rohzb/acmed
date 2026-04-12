"""Error types for acmed.

All runtime-facing failures use explicit error classes so the API surface can fail
closed and return stable reason codes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AcmedError(Exception):
    """Base class for expected acmed failures."""

    code: str
    message: str
    http_status: int = 400

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class ConfigError(AcmedError):
    """Configuration load or validation failure."""
    def __init__(self, message: str) -> None:
        super().__init__("config_error", message, http_status=500)


class ValidationError(AcmedError):
    """Input validation failure for API or internal data."""
    def __init__(self, message: str) -> None:
        super().__init__("validation_error", message, http_status=400)


class AuthenticationError(AcmedError):
    """Authentication failure."""
    def __init__(self, message: str = "authentication failed") -> None:
        super().__init__("authentication_error", message, http_status=401)


class AuthorizationError(AcmedError):
    """Authorization failure."""
    def __init__(self, message: str = "access denied") -> None:
        super().__init__("authorization_error", message, http_status=403)


class ConflictError(AcmedError):
    """Conflict with existing persisted state."""
    def __init__(self, message: str) -> None:
        super().__init__("conflict", message, http_status=409)


class NotFoundError(AcmedError):
    """Requested resource does not exist."""
    def __init__(self, message: str) -> None:
        super().__init__("not_found", message, http_status=404)


class StorageError(AcmedError):
    """Persistence-layer failure."""
    def __init__(self, message: str) -> None:
        super().__init__("storage_error", message, http_status=500)


class WorkerError(AcmedError):
    """Background worker execution failure."""
    def __init__(self, message: str) -> None:
        super().__init__("worker_error", message, http_status=500)


class AcmeProblemError(AcmedError):
    """ACME problem detail error with explicit RFC problem type code."""

    def __init__(self, problem_type: str, detail: str, http_status: int = 400) -> None:
        super().__init__(problem_type, detail, http_status=http_status)
