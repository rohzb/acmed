"""Authentication helpers for admin and broker-authenticated paths."""

from __future__ import annotations

import hmac
import os

from .config import AppConfig
from .errors import AuthenticationError, AuthorizationError


class AuthService:
    """Authenticates API token credentials and performs admin checks."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def authenticate_api_token(self, bearer_token: str | None) -> str:
        if not self._config.identity.api_tokens_enabled:
            raise AuthenticationError("API token authentication disabled")
        if not bearer_token:
            raise AuthenticationError("missing bearer token")

        for token in self._config.identity.api_tokens:
            expected = os.environ.get(token.secret_env)
            if expected is None:
                raise AuthenticationError(f"missing secret env for token {token.token_id}")
            if hmac.compare_digest(expected, bearer_token):
                return token.subject.strip().lower()

        raise AuthenticationError("invalid token")

    def require_admin_subject(self, subject: str) -> None:
        if subject.strip().lower() not in set(self._config.access.admin_subjects):
            raise AuthorizationError("subject is not an admin")
