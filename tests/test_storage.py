from pathlib import Path
import threading

from acmed.models import OrderRequest, PrivateKeyPolicy
from acmed.storage import Storage


def test_dedupe_returns_same_active_order(tmp_path: Path):
    storage = Storage(tmp_path / "acmed.db", tmp_path / "orders")
    request = OrderRequest(
        requester_id="acct-1",
        requester_ip="127.0.0.1",
        request_source="acme",
        dns_names=["a.example.org"],
        common_name="a.example.org",
    )
    first, created = storage.create_order(
        request=request,
        issuer_name="mock",
        proof_handler_name="no-proof",
        challenge_validation_mode="strict",
        private_key_policy=PrivateKeyPolicy.SERVICE_GENERATED,
        max_retries=3,
        ttl_seconds=3600,
    )
    second, created_second = storage.create_order(
        request=request,
        issuer_name="mock",
        proof_handler_name="no-proof",
        challenge_validation_mode="strict",
        private_key_policy=PrivateKeyPolicy.SERVICE_GENERATED,
        max_retries=3,
        ttl_seconds=3600,
    )
    assert created is True
    assert created_second is False
    assert first.id == second.id


def test_artifact_private_key_permissions(tmp_path: Path):
    storage = Storage(tmp_path / "acmed.db", tmp_path / "orders")
    path = storage.write_artifact("order-1", "private.key", "secret", sensitive=True)
    assert oct(path.stat().st_mode & 0o777) == "0o600"


def test_dedupe_distinguishes_challenge_validation_mode(tmp_path: Path):
    storage = Storage(tmp_path / "acmed.db", tmp_path / "orders")
    request = OrderRequest(
        requester_id="acct-1",
        requester_ip="127.0.0.1",
        request_source="acme",
        dns_names=["a.example.org"],
        common_name="a.example.org",
    )
    first, first_created = storage.create_order(
        request=request,
        issuer_name="mock",
        proof_handler_name="no-proof",
        challenge_validation_mode="strict",
        private_key_policy=PrivateKeyPolicy.SERVICE_GENERATED,
        max_retries=3,
        ttl_seconds=3600,
    )
    second, second_created = storage.create_order(
        request=request,
        issuer_name="mock",
        proof_handler_name="no-proof",
        challenge_validation_mode="trusted_bypass",
        private_key_policy=PrivateKeyPolicy.SERVICE_GENERATED,
        max_retries=3,
        ttl_seconds=3600,
    )

    assert first_created is True
    assert second_created is True
    assert first.id != second.id


def test_storage_transactions_are_serialized_across_threads(tmp_path: Path):
    storage = Storage(tmp_path / "acmed.db", tmp_path / "orders")
    errors: list[Exception] = []

    def _nonce_writer():
        try:
            for _ in range(200):
                storage.create_nonce()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def _worker_tick():
        try:
            for _ in range(200):
                storage.expire_eligible_orders()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    t1 = threading.Thread(target=_nonce_writer)
    t2 = threading.Thread(target=_worker_tick)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert errors == []
