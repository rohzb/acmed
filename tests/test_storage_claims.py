from pathlib import Path

from acmed.models import OrderRequest, OrderStatus, PrivateKeyPolicy, utc_now
from acmed.storage import Storage


def test_acme_pending_order_not_claimed_before_finalize(tmp_path: Path):
    storage = Storage(tmp_path / "acmed.db", tmp_path / "orders")
    order, _ = storage.create_order(
        request=OrderRequest(
            requester_id="acc-1",
            requester_ip="10.0.0.10",
            request_source="acme",
            dns_names=["host1.lab.example.org"],
            common_name="host1.lab.example.org",
        ),
        issuer_name="mock",
        proof_handler_name="no-proof",
        challenge_validation_mode="strict",
        private_key_policy=PrivateKeyPolicy.SERVICE_GENERATED,
        max_retries=3,
        ttl_seconds=3600,
    )

    claim = storage.claim_next_order("worker-1", claim_ttl_seconds=60)
    assert claim is None

    storage.set_order_finalize_requested(order.id, enabled=True)
    claim = storage.claim_next_order("worker-1", claim_ttl_seconds=60)
    assert claim is not None
    assert claim.id == order.id
    assert claim.status == OrderStatus.AUTHORIZING


def test_expired_issuing_claim_is_reclaimed(tmp_path: Path):
    storage = Storage(tmp_path / "acmed.db", tmp_path / "orders")
    order, _ = storage.create_order(
        request=OrderRequest(
            requester_id="listener",
            requester_ip="127.0.0.1",
            request_source="listener_certificate",
            dns_names=["acme.lab.example.org"],
            common_name="acme.lab.example.org",
        ),
        issuer_name="mock",
        proof_handler_name="no-proof",
        challenge_validation_mode="strict",
        private_key_policy=PrivateKeyPolicy.SERVICE_GENERATED,
        max_retries=3,
        ttl_seconds=3600,
    )

    first_claim = storage.claim_next_order("worker-1", claim_ttl_seconds=1)
    assert first_claim is not None
    storage.transition_order_status(order.id, OrderStatus.AUTHORIZING, OrderStatus.AUTHORIZED)
    storage.transition_order_status(order.id, OrderStatus.AUTHORIZED, OrderStatus.ISSUING)

    with storage._tx() as conn:
        conn.execute(
            """
            UPDATE orders
            SET claim_expires_at = ?
            WHERE id = ?
            """,
            ((utc_now().replace(year=2025)).isoformat(), order.id),
        )

    reclaimed = storage.claim_next_order("worker-2", claim_ttl_seconds=60)
    assert reclaimed is not None
    assert reclaimed.id == order.id
    assert reclaimed.status == OrderStatus.ISSUING
    assert reclaimed.claimed_by == "worker-2"
