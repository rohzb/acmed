"""Background worker loop for order authorization, proof, and issuance."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime

from .audit import make_audit_event, redact_sensitive
from .authorizers import AuthorizerInput, AuthorizerService
from .config import AppConfig
from .errors import AuthorizationError
from .issuers import IssueRequest, default_issuer_backends
from .models import Order, OrderStatus, utc_now
from .proofs import InventoryAssertionProofHandler, NoProofHandler, ProofInput
from .policy import policy_matches_dns
from .storage import Storage


@dataclass(slots=True)
class RetryDecision:
    """Retry classification outcome for worker error handling."""

    retryable: bool
    reason: str


class Worker:
    """Polls and processes pending work using policy-selected plugins."""

    def __init__(self, config: AppConfig, storage: Storage, worker_id: str = "worker-1") -> None:
        self._config = config
        self._storage = storage
        self._worker_id = worker_id
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._issuer_backends = default_issuer_backends()
        self._authorizers = AuthorizerService(config)
        self._proof_handlers = {}
        for handler in self._config.proof_handlers:
            if handler.type == "none":
                self._proof_handlers[handler.name] = NoProofHandler(name=handler.name)
            elif handler.type == "inventory_assertion":
                self._proof_handlers[handler.name] = InventoryAssertionProofHandler(
                    name=handler.name,
                    inventory_source=handler.inventory_source or "",
                )

    def start(self) -> None:
        """Start for Worker.

        Returns:
            `None`.
        """
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.run_forever, name=self._worker_id, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop for Worker.

        Returns:
            `None`.
        """
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def run_forever(self) -> None:
        """Run forever for Worker.

        Returns:
            `None`.
        """
        while not self._stop.is_set():
            self._storage.expire_eligible_orders()
            order = self._storage.claim_next_order(
                worker_id=self._worker_id,
                claim_ttl_seconds=self._config.orders.claim_ttl_seconds,
            )
            if order is None:
                time.sleep(self._config.workers.poll_interval_seconds)
                continue
            self._process_claimed_order(order)

    def _process_claimed_order(self, order: Order) -> None:
        try:
            if order.status == OrderStatus.AUTHORIZING:
                self._run_authorization(order)
                self._run_proof(order)
                self._storage.transition_order_status(order.id, OrderStatus.AUTHORIZED, OrderStatus.ISSUING)
            self._run_issuance(order.id)
        except AuthorizationError as exc:
            self._storage.mark_terminal(order.id, status=OrderStatus.DENIED, error_message=exc.message)
            self._write_audit(order.id, "order.denied", "worker", self._worker_id, exc.message, {})
        except Exception as exc:  # noqa: BLE001
            decision = self._classify_retry(exc)
            error_message = redact_sensitive(str(exc))
            self._storage.mark_terminal(order.id, status=OrderStatus.FAILED, error_message=error_message)
            self._write_audit(
                order.id,
                "order.failed",
                "worker",
                self._worker_id,
                error_message,
                {"retryable": decision.retryable, "reason": decision.reason},
            )
            if decision.retryable:
                try:
                    self._storage.requeue_retry(order.id)
                except Exception:
                    pass
        finally:
            self._storage.release_claim(order.id, self._worker_id)

    def _run_authorization(self, order: Order) -> None:
        candidate_policies = [
            policy
            for policy in self._config.policies
            if policy.proof_handler == order.proof_handler_name
            and order.issuer_name in policy.allowed_issuers
            and policy_matches_dns(policy, order.dns_names)
        ]
        if not candidate_policies:
            raise AuthorizationError("no matching policy for claimed order")
        selected_policy = candidate_policies[0]

        request_ip = order.requester_ip if order.requester_ip else (order.requester_id if _looks_like_ip(order.requester_id) else None)
        authorized_names = self._authorizers.require_authorizers(
            selected_policy.authorizers,
            AuthorizerInput(
                requester_id=order.requester_id,
                request_ip=request_ip,
                dns_names=order.dns_names,
            ),
        )
        self._storage.transition_order_status(order.id, OrderStatus.AUTHORIZING, OrderStatus.AUTHORIZED)
        self._write_audit(
            order.id,
            "order.authorized",
            "worker",
            self._worker_id,
            "authorizer checks passed",
            {"authorizers": sorted(authorized_names)},
        )

    def _run_proof(self, order: Order) -> None:
        handler = self._proof_handlers.get(order.proof_handler_name)
        if handler is None:
            raise AuthorizationError(f"unknown proof handler: {order.proof_handler_name}")
        result = handler.evaluate(
            ProofInput(order_id=order.id, requester_id=order.requester_id, dns_names=order.dns_names)
        )
        if not result.passed:
            raise AuthorizationError(result.reason)
        self._write_audit(
            order.id,
            "order.proof_satisfied",
            "worker",
            self._worker_id,
            result.reason,
            result.evidence,
        )

    def _run_issuance(self, order_id: str) -> None:
        order = self._storage.get_order(order_id)
        issuer_profile = next((item for item in self._config.issuers if item.name == order.issuer_name), None)
        if issuer_profile is None:
            raise RuntimeError(f"unknown issuer profile: {order.issuer_name}")

        issuer = self._issuer_backends.get(issuer_profile.type)
        if issuer is None:
            raise RuntimeError(f"issuer backend not registered: {issuer_profile.type}")

        artifact_dir = self._storage.create_artifact_dir(order.id)
        started_at = utc_now()
        result = issuer.issue(
            profile=issuer_profile,
            request=IssueRequest(
                order_id=order.id,
                dns_names=order.dns_names,
                common_name=order.common_name,
                csr_pem=None,
                artifacts_dir=str(artifact_dir),
            ),
        )
        finished_at = utc_now()

        stdout_path = self._storage.write_artifact(order.id, "issuer-output.log", result.stdout, sensitive=False)
        stderr_path = self._storage.write_artifact(order.id, "challenge-output.log", result.stderr, sensitive=False)

        self._storage.write_issuance_attempt(
            order_id=order.id,
            issuer_name=order.issuer_name,
            attempt_number=order.retry_count + 1,
            command=result.command,
            exit_code=result.exit_code,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            started_at=started_at,
            finished_at=finished_at,
            result_code=result.result_code,
        )

        if not result.success:
            raise RuntimeError(f"issuer failed with exit code {result.exit_code}")

        if result.private_key_pem:
            self._storage.write_artifact(order.id, "private.key", result.private_key_pem, sensitive=True)
        if result.certificate_pem:
            self._storage.write_artifact(order.id, "certificate.pem", result.certificate_pem)
        if result.chain_pem:
            self._storage.write_artifact(order.id, "chain.pem", result.chain_pem)
        if result.fullchain_pem:
            self._storage.write_artifact(order.id, "fullchain.pem", result.fullchain_pem)

        self._storage.mark_terminal(order.id, status=OrderStatus.ISSUED)
        self._write_audit(
            order.id,
            "order.issued",
            "worker",
            self._worker_id,
            "issuance completed",
            {"issuer": order.issuer_name, "finished_at": _iso(finished_at)},
        )

    def _classify_retry(self, exc: Exception) -> RetryDecision:
        message = str(exc).lower()
        if "timeout" in message or "database is locked" in message:
            return RetryDecision(retryable=True, reason="transient failure")
        if "authorization" in message or "policy" in message or "csr" in message:
            return RetryDecision(retryable=False, reason="non-retryable validation or authorization error")
        return RetryDecision(retryable=False, reason="default non-retryable")

    def _write_audit(
        self,
        order_id: str | None,
        event_type: str,
        actor_type: str,
        actor_id: str,
        message: str,
        metadata: dict[str, object],
    ) -> None:
        event = make_audit_event(
            order_id=order_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            message=message,
            metadata=metadata,
        )
        self._storage.write_audit_event(
            event_id=event.id,
            order_id=event.order_id,
            event_type=event.event_type,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            message=event.message,
            metadata=event.metadata,
            created_at=event.created_at,
        )


def _iso(value: datetime) -> str:
    """Return ISO-8601 text for audit metadata values."""

    return value.isoformat()


def _looks_like_ip(value: str) -> bool:
    """Heuristic check whether requester id resembles an IP address."""

    return "." in value or ":" in value
