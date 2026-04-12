"""Shared API handlers: health and admin resources.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from .auth import AuthService
from .models import Order
from .storage import Storage
from .utils import utc_iso


class ApiService:
    """Transport-agnostic handlers for shared API resources."""

    def __init__(self, storage: Storage, auth_service: AuthService) -> None:
        self._storage = storage
        self._auth = auth_service

    def health(self) -> tuple[int, dict[str, object], dict[str, str]]:
        """Health for ApiService.

        Returns:
            Result value matching `tuple[int, dict[str, object], dict[str, str]]`.
        """
        return 200, {"status": "ok"}, {"Content-Type": "application/json"}

    def list_admin_orders(self, bearer_token: str | None, limit: int = 100) -> tuple[int, dict[str, object], dict[str, str]]:
        """List admin orders for ApiService.

        Args:
            bearer_token: Bearer token from the Authorization header.
            limit: Maximum number of records to return.

        Returns:
            Result value matching `tuple[int, dict[str, object], dict[str, str]]`.
        """
        subject = self._auth.authenticate_api_token(bearer_token)
        self._auth.require_admin_subject(subject)
        orders = [self._serialize_order(item) for item in self._storage.list_orders(limit=limit)]
        return 200, {"orders": orders}, {"Content-Type": "application/json"}

    def _serialize_order(self, order: Order) -> dict[str, object]:
        data = asdict(order)
        for key in ("not_before", "not_after", "claimed_at", "claim_expires_at", "created_at", "updated_at", "expires_at"):
            data[key] = utc_iso(data[key])
        data["dns_names"] = list(order.dns_names)
        return data

    @staticmethod
    def encode_json(body: dict[str, object]) -> bytes:
        """Encode json for ApiService.

        Args:
            body: JSON-serializable response body mapping.

        Returns:
            Result value matching `bytes`.
        """
        return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
