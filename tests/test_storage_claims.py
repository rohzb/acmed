from pathlib import Path

from acmed.models import OrderRequest, OrderStatus, PrivateKeyPolicy
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
