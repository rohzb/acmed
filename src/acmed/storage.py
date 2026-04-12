"""SQLite persistence and artifact storage for acmed."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from .errors import ConflictError, NotFoundError, StorageError
from .models import (
    ALLOWED_TRANSITIONS,
    CsrSource,
    Order,
    OrderRequest,
    OrderStatus,
    PrivateKeyPolicy,
    compute_dedupe_key,
    new_order_expiry,
    utc_now,
)


def _dt_to_text(value: datetime | None) -> str | None:
    """Serialize datetime to UTC ISO-8601 text for SQLite storage."""

    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def _text_to_dt(value: str | None) -> datetime | None:
    """Parse ISO-8601 text from SQLite into datetime."""

    if value is None:
        return None
    return datetime.fromisoformat(value)


class Storage:
    """SQLite-backed repository and artifact writer."""

    def __init__(self, sqlite_path: Path, artifacts_root: Path) -> None:
        self._sqlite_path = sqlite_path
        self._artifacts_root = artifacts_root
        self._artifacts_root.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._sqlite_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._tx_lock = threading.RLock()
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self.initialize_schema()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._tx_lock:
            try:
                yield self._conn
                self._conn.commit()
            except sqlite3.Error as exc:
                self._conn.rollback()
                raise StorageError(f"sqlite error: {exc}") from exc

    def initialize_schema(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS orders (
          id TEXT PRIMARY KEY,
          status TEXT NOT NULL,
          requester_id TEXT NOT NULL,
          requester_ip TEXT,
          request_source TEXT NOT NULL,
          dns_names_json TEXT NOT NULL,
          common_name TEXT,
          issuer_name TEXT NOT NULL,
          proof_handler_name TEXT NOT NULL,
          challenge_validation_mode TEXT NOT NULL DEFAULT 'strict',
          private_key_policy TEXT NOT NULL,
          csr_source TEXT NOT NULL,
          not_before TEXT,
          not_after TEXT,
          claimed_by TEXT,
          claimed_at TEXT,
          claim_expires_at TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          expires_at TEXT NOT NULL,
          retry_count INTEGER NOT NULL,
          max_retries INTEGER NOT NULL,
          error_message TEXT,
          dedupe_key TEXT NOT NULL,
          idempotency_key TEXT,
          finalize_requested INTEGER NOT NULL DEFAULT 0
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_active_dedupe
            ON orders(dedupe_key)
            WHERE status IN ('pending','authorizing','authorized','issuing');
        CREATE INDEX IF NOT EXISTS idx_orders_claim ON orders(status, claim_expires_at);

        CREATE TABLE IF NOT EXISTS issuance_attempts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          order_id TEXT NOT NULL,
          issuer_name TEXT NOT NULL,
          attempt_number INTEGER NOT NULL,
          command TEXT NOT NULL,
          exit_code INTEGER NOT NULL,
          stdout_path TEXT NOT NULL,
          stderr_path TEXT NOT NULL,
          started_at TEXT NOT NULL,
          finished_at TEXT NOT NULL,
          result_code TEXT NOT NULL,
          FOREIGN KEY(order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS audit_events (
          id TEXT PRIMARY KEY,
          order_id TEXT,
          event_type TEXT NOT NULL,
          actor_type TEXT NOT NULL,
          actor_id TEXT NOT NULL,
          message TEXT NOT NULL,
          metadata_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS acme_accounts (
          id TEXT PRIMARY KEY,
          status TEXT NOT NULL,
          jwk_thumbprint TEXT NOT NULL UNIQUE,
          jwk_json TEXT NOT NULL,
          contact_json TEXT NOT NULL,
          eab_kid TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS acme_account_orders (
          account_id TEXT NOT NULL,
          order_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY(account_id, order_id),
          FOREIGN KEY(account_id) REFERENCES acme_accounts(id),
          FOREIGN KEY(order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS acme_authorizations (
          id TEXT PRIMARY KEY,
          order_id TEXT NOT NULL,
          identifier_type TEXT NOT NULL,
          identifier_value TEXT NOT NULL,
          status TEXT NOT NULL,
          expires_at TEXT NOT NULL,
          wildcard INTEGER NOT NULL,
          FOREIGN KEY(order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS acme_challenges (
          id TEXT PRIMARY KEY,
          authorization_id TEXT NOT NULL,
          challenge_type TEXT NOT NULL,
          token TEXT NOT NULL,
          status TEXT NOT NULL,
          validated_at TEXT,
          error_code TEXT,
          error_detail TEXT,
          FOREIGN KEY(authorization_id) REFERENCES acme_authorizations(id)
        );

        CREATE TABLE IF NOT EXISTS nonces (
          nonce TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          used INTEGER NOT NULL DEFAULT 0
        );
        """
        with self._tx() as conn:
            conn.executescript(schema)
        self._ensure_schema_upgrades()

    def _ensure_schema_upgrades(self) -> None:
        """Apply lightweight additive schema upgrades for existing DB files."""
        with self._tx() as conn:
            order_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(orders)").fetchall()
            }
            if "requester_ip" not in order_columns:
                conn.execute("ALTER TABLE orders ADD COLUMN requester_ip TEXT")
            if "finalize_requested" not in order_columns:
                conn.execute(
                    "ALTER TABLE orders ADD COLUMN finalize_requested INTEGER NOT NULL DEFAULT 0"
                )
            if "challenge_validation_mode" not in order_columns:
                conn.execute(
                    "ALTER TABLE orders ADD COLUMN challenge_validation_mode TEXT NOT NULL DEFAULT 'strict'"
                )

            account_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(acme_accounts)").fetchall()
            }
            if "jwk_json" not in account_columns:
                conn.execute("ALTER TABLE acme_accounts ADD COLUMN jwk_json TEXT")
                conn.execute(
                    "UPDATE acme_accounts SET jwk_json = '{}' WHERE jwk_json IS NULL OR jwk_json = ''"
                )

    def close(self) -> None:
        self._conn.close()

    def _row_to_order(self, row: sqlite3.Row) -> Order:
        return Order(
            id=row["id"],
            status=OrderStatus(row["status"]),
            requester_id=row["requester_id"],
            requester_ip=row["requester_ip"],
            request_source=row["request_source"],
            dns_names=json.loads(row["dns_names_json"]),
            common_name=row["common_name"],
            issuer_name=row["issuer_name"],
            proof_handler_name=row["proof_handler_name"],
            challenge_validation_mode=row["challenge_validation_mode"] or "strict",
            private_key_policy=PrivateKeyPolicy(row["private_key_policy"]),
            csr_source=CsrSource(row["csr_source"]),
            not_before=_text_to_dt(row["not_before"]),
            not_after=_text_to_dt(row["not_after"]),
            claimed_by=row["claimed_by"],
            claimed_at=_text_to_dt(row["claimed_at"]),
            claim_expires_at=_text_to_dt(row["claim_expires_at"]),
            created_at=_text_to_dt(row["created_at"]) or utc_now(),
            updated_at=_text_to_dt(row["updated_at"]) or utc_now(),
            expires_at=_text_to_dt(row["expires_at"]) or utc_now(),
            retry_count=int(row["retry_count"]),
            max_retries=int(row["max_retries"]),
            error_message=row["error_message"],
            dedupe_key=row["dedupe_key"],
        )

    def create_order(
        self,
        request: OrderRequest,
        issuer_name: str,
        proof_handler_name: str,
        challenge_validation_mode: str,
        private_key_policy: PrivateKeyPolicy,
        max_retries: int,
        ttl_seconds: int,
    ) -> tuple[Order, bool]:
        order_id = str(uuid.uuid4())
        now = utc_now()
        csr_source = CsrSource.CLIENT_PROVIDED if request.csr_pem else CsrSource.SERVICE_GENERATED
        dedupe_key = compute_dedupe_key(
            requester_id=request.requester_id,
            dns_names=request.dns_names,
            issuer_name=issuer_name,
            csr_source=csr_source,
            private_key_policy=private_key_policy,
            challenge_validation_mode=challenge_validation_mode,
        )

        with self._tx() as conn:
            existing = conn.execute(
                """
                SELECT * FROM orders
                WHERE dedupe_key = ?
                  AND status IN ('pending','authorizing','authorized','issuing')
                LIMIT 1
                """,
                (dedupe_key,),
            ).fetchone()
            if existing:
                existing_order = self._row_to_order(existing)
                return existing_order, False

            if request.idempotency_key:
                conflict = conn.execute(
                    """
                    SELECT * FROM orders
                    WHERE requester_id = ?
                      AND idempotency_key = ?
                      AND dedupe_key != ?
                    LIMIT 1
                    """,
                    (request.requester_id, request.idempotency_key, dedupe_key),
                ).fetchone()
                if conflict:
                    raise ConflictError("idempotency_key reused with different payload")

            expires_at = new_order_expiry(ttl_seconds)
            conn.execute(
                """
                INSERT INTO orders(
                  id, status, requester_id, requester_ip, request_source, dns_names_json, common_name,
                  issuer_name, proof_handler_name, challenge_validation_mode, private_key_policy, csr_source,
                  not_before, not_after, claimed_by, claimed_at, claim_expires_at,
                  created_at, updated_at, expires_at, retry_count, max_retries,
                  error_message, dedupe_key, idempotency_key, finalize_requested
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    OrderStatus.PENDING,
                    request.requester_id,
                    request.requester_ip,
                    request.request_source,
                    json.dumps(request.dns_names),
                    request.common_name,
                    issuer_name,
                    proof_handler_name,
                    challenge_validation_mode,
                    private_key_policy,
                    csr_source,
                    _dt_to_text(request.not_before),
                    _dt_to_text(request.not_after),
                    None,
                    None,
                    None,
                    _dt_to_text(now),
                    _dt_to_text(now),
                    _dt_to_text(expires_at),
                    0,
                    max_retries,
                    None,
                    dedupe_key,
                    request.idempotency_key,
                    0,
                ),
            )

            created = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not created:
                raise StorageError("order insert failed")
            return self._row_to_order(created), True

    def get_order(self, order_id: str) -> Order:
        row = self._conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"order {order_id} not found")
        return self._row_to_order(row)

    def list_orders(self, limit: int = 100) -> list[Order]:
        rows = self._conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_order(row) for row in rows]

    def transition_order_status(self, order_id: str, from_status: OrderStatus, to_status: OrderStatus) -> None:
        if to_status not in ALLOWED_TRANSITIONS[from_status]:
            raise StorageError(f"illegal state transition: {from_status}->{to_status}")

        now = utc_now()
        with self._tx() as conn:
            changed = conn.execute(
                """
                UPDATE orders
                SET status = ?, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (to_status, _dt_to_text(now), order_id, from_status),
            )
            if changed.rowcount != 1:
                raise StorageError(f"transition failed for {order_id}")

    def claim_next_order(self, worker_id: str, claim_ttl_seconds: int) -> Order | None:
        now = utc_now()
        now_text = _dt_to_text(now)
        expires_text = _dt_to_text(now + timedelta(seconds=claim_ttl_seconds))
        with self._tx() as conn:
            row = conn.execute(
                """
                SELECT id, status FROM orders
                WHERE status IN ('pending','authorized')
                  AND expires_at > ?
                  AND (claim_expires_at IS NULL OR claim_expires_at <= ?)
                  AND (
                    status != 'pending'
                    OR request_source != 'acme'
                    OR finalize_requested = 1
                  )
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (now_text, now_text),
            ).fetchone()
            if row is None:
                return None

            current = OrderStatus(row["status"])
            next_state = OrderStatus.AUTHORIZING if current == OrderStatus.PENDING else OrderStatus.ISSUING
            if next_state not in ALLOWED_TRANSITIONS[current]:
                raise StorageError("invalid claim transition")

            updated = conn.execute(
                """
                UPDATE orders
                SET status = ?, claimed_by = ?, claimed_at = ?, claim_expires_at = ?, updated_at = ?
                WHERE id = ?
                  AND status = ?
                  AND (claim_expires_at IS NULL OR claim_expires_at <= ?)
                """,
                (
                    next_state,
                    worker_id,
                    now_text,
                    expires_text,
                    now_text,
                    row["id"],
                    current,
                    now_text,
                ),
            )
            if updated.rowcount != 1:
                return None

            claimed_row = conn.execute("SELECT * FROM orders WHERE id = ?", (row["id"],)).fetchone()
            if not claimed_row:
                raise StorageError("claimed order not found")
            return self._row_to_order(claimed_row)

    def release_claim(self, order_id: str, worker_id: str) -> None:
        with self._tx() as conn:
            conn.execute(
                """
                UPDATE orders
                SET claimed_by = NULL, claimed_at = NULL, claim_expires_at = NULL, updated_at = ?
                WHERE id = ? AND claimed_by = ?
                """,
                (_dt_to_text(utc_now()), order_id, worker_id),
            )

    def mark_terminal(self, order_id: str, status: OrderStatus, error_message: str | None = None) -> None:
        if status not in {OrderStatus.ISSUED, OrderStatus.FAILED, OrderStatus.DENIED, OrderStatus.EXPIRED}:
            raise StorageError(f"unsupported terminal status: {status}")

        with self._tx() as conn:
            conn.execute(
                """
                UPDATE orders
                SET status = ?, error_message = ?, claimed_by = NULL, claimed_at = NULL,
                    claim_expires_at = NULL, updated_at = ?
                WHERE id = ?
                """,
                (status, error_message, _dt_to_text(utc_now()), order_id),
            )

    def requeue_retry(self, order_id: str) -> None:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT retry_count, max_retries, status FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()
            if not row:
                raise NotFoundError(f"order {order_id} not found")
            if row["status"] != OrderStatus.FAILED:
                raise StorageError("can only retry failed orders")
            if row["retry_count"] >= row["max_retries"]:
                raise StorageError("retry limit exhausted")

            conn.execute(
                """
                UPDATE orders
                SET status = ?, retry_count = retry_count + 1, error_message = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (OrderStatus.PENDING, _dt_to_text(utc_now()), order_id),
            )

    def expire_eligible_orders(self) -> int:
        now = _dt_to_text(utc_now())
        with self._tx() as conn:
            changed = conn.execute(
                """
                UPDATE orders
                SET status = 'expired', error_message = 'order expired before completion',
                    claimed_by = NULL, claimed_at = NULL, claim_expires_at = NULL,
                    updated_at = ?
                WHERE status IN ('pending','authorized') AND expires_at <= ?
                """,
                (now, now),
            )
            return changed.rowcount

    def write_issuance_attempt(
        self,
        order_id: str,
        issuer_name: str,
        attempt_number: int,
        command: str,
        exit_code: int,
        stdout_path: str,
        stderr_path: str,
        started_at: datetime,
        finished_at: datetime,
        result_code: str,
    ) -> None:
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO issuance_attempts(
                  order_id, issuer_name, attempt_number, command, exit_code,
                  stdout_path, stderr_path, started_at, finished_at, result_code
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    issuer_name,
                    attempt_number,
                    command,
                    exit_code,
                    stdout_path,
                    stderr_path,
                    _dt_to_text(started_at),
                    _dt_to_text(finished_at),
                    result_code,
                ),
            )

    def write_audit_event(
        self,
        event_id: str,
        order_id: str | None,
        event_type: str,
        actor_type: str,
        actor_id: str,
        message: str,
        metadata: dict[str, Any],
        created_at: datetime,
    ) -> None:
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO audit_events(
                  id, order_id, event_type, actor_type, actor_id,
                  message, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    order_id,
                    event_type,
                    actor_type,
                    actor_id,
                    message,
                    json.dumps(metadata),
                    _dt_to_text(created_at),
                ),
            )

    def create_artifact_dir(self, order_id: str) -> Path:
        path = self._artifacts_root / order_id
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(path, 0o700)
        return path

    def write_artifact(self, order_id: str, filename: str, content: str, sensitive: bool = False) -> Path:
        order_dir = self.create_artifact_dir(order_id)
        path = order_dir / filename
        temp_path = order_dir / f".{filename}.tmp"
        mode = 0o600 if sensitive else 0o640
        temp_path.write_text(content, encoding="utf-8")
        os.chmod(temp_path, mode)
        temp_path.replace(path)
        os.chmod(path, mode)
        return path

    def create_nonce(self) -> str:
        nonce = uuid.uuid4().hex
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO nonces(nonce, created_at, used) VALUES (?, ?, 0)",
                (nonce, _dt_to_text(utc_now())),
            )
        return nonce

    def consume_nonce(self, nonce: str) -> bool:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT used FROM nonces WHERE nonce = ?",
                (nonce,),
            ).fetchone()
            if not row or row["used"]:
                return False
            conn.execute("UPDATE nonces SET used = 1 WHERE nonce = ?", (nonce,))
            return True

    def get_or_create_acme_account(
        self,
        jwk_thumbprint: str,
        jwk: dict[str, Any],
        contact: list[str],
        eab_kid: str | None,
    ) -> dict[str, Any]:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT * FROM acme_accounts WHERE jwk_thumbprint = ?",
                (jwk_thumbprint,),
            ).fetchone()
            if row:
                return dict(row)

            account_id = str(uuid.uuid4())
            now = _dt_to_text(utc_now())
            conn.execute(
                """
                INSERT INTO acme_accounts(
                  id, status, jwk_thumbprint, jwk_json, contact_json, eab_kid, created_at, updated_at
                )
                VALUES (?, 'valid', ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id,
                    jwk_thumbprint,
                    json.dumps(jwk, sort_keys=True),
                    json.dumps(contact),
                    eab_kid,
                    now,
                    now,
                ),
            )
            created = conn.execute("SELECT * FROM acme_accounts WHERE id = ?", (account_id,)).fetchone()
            if not created:
                raise StorageError("failed to create account")
            return dict(created)

    def get_acme_account(self, account_id: str) -> dict[str, Any]:
        row = self._conn.execute("SELECT * FROM acme_accounts WHERE id = ?", (account_id,)).fetchone()
        if not row:
            raise NotFoundError(f"account {account_id} not found")
        return dict(row)

    def get_acme_account_jwk(self, account_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT jwk_json FROM acme_accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["jwk_json"])
        except Exception:  # noqa: BLE001
            return None

    def find_acme_account_by_thumbprint(self, jwk_thumbprint: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM acme_accounts WHERE jwk_thumbprint = ?",
            (jwk_thumbprint,),
        ).fetchone()
        return dict(row) if row else None

    def add_acme_account_order_link(self, account_id: str, order_id: str) -> None:
        with self._tx() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO acme_account_orders(account_id, order_id, created_at)
                VALUES (?, ?, ?)
                """,
                (account_id, order_id, _dt_to_text(utc_now())),
            )

    def account_owns_order(self, account_id: str, order_id: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1 FROM acme_account_orders
            WHERE account_id = ? AND order_id = ?
            """,
            (account_id, order_id),
        ).fetchone()
        return row is not None

    def list_account_order_ids(self, account_id: str) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT order_id FROM acme_account_orders
            WHERE account_id = ?
            ORDER BY created_at DESC
            """,
            (account_id,),
        ).fetchall()
        return [row["order_id"] for row in rows]

    def create_acme_authorization(self, order_id: str, identifier_value: str) -> str:
        authz_id = str(uuid.uuid4())
        wildcard = int(identifier_value.startswith("*."))
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO acme_authorizations(
                  id, order_id, identifier_type, identifier_value, status, expires_at, wildcard
                )
                VALUES (?, ?, 'dns', ?, 'pending', ?, ?)
                """,
                (
                    authz_id,
                    order_id,
                    identifier_value,
                    _dt_to_text(new_order_expiry(3600)),
                    wildcard,
                ),
            )
        return authz_id

    def create_acme_challenge(self, authorization_id: str, challenge_type: str) -> str:
        challenge_id = str(uuid.uuid4())
        token = uuid.uuid4().hex
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO acme_challenges(
                  id, authorization_id, challenge_type, token, status,
                  validated_at, error_code, error_detail
                )
                VALUES (?, ?, ?, ?, 'pending', NULL, NULL, NULL)
                """,
                (challenge_id, authorization_id, challenge_type, token),
            )
        return challenge_id

    def list_acme_authorizations_for_order(self, order_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM acme_authorizations WHERE order_id = ? ORDER BY id",
            (order_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_acme_challenges_for_authorization(self, authorization_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM acme_challenges WHERE authorization_id = ? ORDER BY id",
            (authorization_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_acme_challenge(self, challenge_id: str) -> dict[str, Any]:
        row = self._conn.execute("SELECT * FROM acme_challenges WHERE id = ?", (challenge_id,)).fetchone()
        if not row:
            raise NotFoundError(f"challenge {challenge_id} not found")
        return dict(row)

    def set_acme_challenge_status(
        self,
        challenge_id: str,
        status: str,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        validated_at = _dt_to_text(utc_now()) if status == "valid" else None
        with self._tx() as conn:
            conn.execute(
                """
                UPDATE acme_challenges
                SET status = ?, validated_at = ?, error_code = ?, error_detail = ?
                WHERE id = ?
                """,
                (status, validated_at, error_code, error_detail, challenge_id),
            )
            link = conn.execute(
                "SELECT authorization_id FROM acme_challenges WHERE id = ?",
                (challenge_id,),
            ).fetchone()
            if not link:
                return
            auth_status = "valid" if status == "valid" else "invalid"
            conn.execute(
                "UPDATE acme_authorizations SET status = ? WHERE id = ?",
                (auth_status, link["authorization_id"]),
            )

    def set_order_finalize_requested(self, order_id: str, enabled: bool) -> None:
        with self._tx() as conn:
            conn.execute(
                "UPDATE orders SET finalize_requested = ?, updated_at = ? WHERE id = ?",
                (1 if enabled else 0, _dt_to_text(utc_now()), order_id),
            )

    def is_order_finalize_requested(self, order_id: str) -> bool:
        row = self._conn.execute(
            "SELECT finalize_requested FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if not row:
            raise NotFoundError(f"order {order_id} not found")
        return bool(row["finalize_requested"])

    def get_order_id_for_authorization(self, authorization_id: str) -> str:
        row = self._conn.execute(
            "SELECT order_id FROM acme_authorizations WHERE id = ?",
            (authorization_id,),
        ).fetchone()
        if not row:
            raise NotFoundError(f"authorization {authorization_id} not found")
        return str(row["order_id"])

    def get_order_id_for_challenge(self, challenge_id: str) -> str:
        row = self._conn.execute(
            """
            SELECT a.order_id
            FROM acme_challenges c
            JOIN acme_authorizations a ON a.id = c.authorization_id
            WHERE c.id = ?
            """,
            (challenge_id,),
        ).fetchone()
        if not row:
            raise NotFoundError(f"challenge {challenge_id} not found")
        return str(row["order_id"])

    def get_account_id_for_order(self, order_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT account_id FROM acme_account_orders WHERE order_id = ? LIMIT 1",
            (order_id,),
        ).fetchone()
        return str(row["account_id"]) if row else None

    def get_challenge_validation_context(self, challenge_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT c.id AS challenge_id, c.challenge_type, c.token, c.status AS challenge_status,
                   a.id AS authorization_id, a.identifier_value, a.status AS authorization_status,
                   a.order_id, acc.id AS account_id, acc.jwk_thumbprint
            FROM acme_challenges c
            JOIN acme_authorizations a ON a.id = c.authorization_id
            JOIN acme_account_orders ao ON ao.order_id = a.order_id
            JOIN acme_accounts acc ON acc.id = ao.account_id
            WHERE c.id = ?
            LIMIT 1
            """,
            (challenge_id,),
        ).fetchone()
        if not row:
            raise NotFoundError(f"challenge {challenge_id} not found")
        return dict(row)
