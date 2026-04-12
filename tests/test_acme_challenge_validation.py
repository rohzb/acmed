import hashlib
from types import SimpleNamespace

import acmed.acme_api as acme_api_module
from acmed.acme_api import AcmeApiService, SignedAcmeRequest


def test_dns_01_validation_success(monkeypatch):
    service = object.__new__(AcmeApiService)
    token = "tok123"
    thumbprint = "thumb456"
    key_auth = f"{token}.{thumbprint}"
    expected_txt = acme_api_module._b64url_nopad(hashlib.sha256(key_auth.encode("utf-8")).digest())

    monkeypatch.setattr(acme_api_module, "_query_txt_records", lambda name: {expected_txt})
    ok, code, detail = service._validate_dns_01(
        {
            "identifier_value": "host1.lab.example.org",
            "token": token,
            "jwk_thumbprint": thumbprint,
        }
    )

    assert ok is True
    assert code is None
    assert detail is None


def test_dns_01_validation_mismatch(monkeypatch):
    service = object.__new__(AcmeApiService)
    monkeypatch.setattr(acme_api_module, "_query_txt_records", lambda name: {"wrong"})

    ok, code, detail = service._validate_dns_01(
        {
            "identifier_value": "host1.lab.example.org",
            "token": "tok",
            "jwk_thumbprint": "thumb",
        }
    )

    assert ok is False
    assert code == "unauthorized"
    assert "mismatch" in (detail or "")


def test_challenge_headers_include_up_link(monkeypatch):
    service = object.__new__(AcmeApiService)

    class _Storage:
        @staticmethod
        def create_nonce() -> str:
            return "nonce-1"

    service._storage = _Storage()  # type: ignore[attr-defined]

    headers = service._challenge_headers(
        base_url="https://acme.example.org",
        authorization_id="authz-123",
    )

    assert headers["Replay-Nonce"] == "nonce-1"
    assert headers["Link"] == '<https://acme.example.org/acme/authz/authz-123>;rel="up"'


def test_acknowledge_challenge_trusted_bypass_sets_valid_without_validation():
    service = object.__new__(AcmeApiService)

    class _Storage:
        def __init__(self):
            self.status_updates: list[tuple[str, str]] = []

        @staticmethod
        def get_order_id_for_challenge(challenge_id: str) -> str:
            assert challenge_id == "challenge-1"
            return "order-1"

        @staticmethod
        def get_challenge_validation_context(challenge_id: str) -> dict[str, str]:
            assert challenge_id == "challenge-1"
            return {"challenge_status": "pending"}

        def set_acme_challenge_status(self, challenge_id: str, status: str, error_code=None, error_detail=None) -> None:
            self.status_updates.append((challenge_id, status))

        @staticmethod
        def get_acme_challenge(challenge_id: str) -> dict[str, str]:
            return {
                "id": challenge_id,
                "authorization_id": "authz-1",
                "challenge_type": "http-01",
                "status": "valid",
                "token": "tok-1",
            }

        @staticmethod
        def create_nonce() -> str:
            return "nonce-1"

        @staticmethod
        def get_order(order_id: str):
            assert order_id == "order-1"
            return SimpleNamespace(challenge_validation_mode="trusted_bypass")

    storage = _Storage()
    service._storage = storage  # type: ignore[attr-defined]
    service._require_account_from_kid = lambda req: "acc-1"  # type: ignore[attr-defined]
    service._require_order_ownership = lambda account_id, order_id: None  # type: ignore[attr-defined]
    service._validate_challenge = lambda context: (_ for _ in ()).throw(AssertionError("should not validate"))  # type: ignore[attr-defined]

    req = SignedAcmeRequest(
        url="https://acme.example.org/acme/challenge/challenge-1",
        nonce="nonce-1",
        payload={},
        payload_raw=b"{}",
        kid="https://acme.example.org/acme/account/acc-1",
    )
    status, body, headers = service.acknowledge_challenge(req, "challenge-1", "https://acme.example.org")

    assert status == 200
    assert body["status"] == "valid"
    assert storage.status_updates == [("challenge-1", "valid")]
    assert headers["Link"] == '<https://acme.example.org/acme/authz/authz-1>;rel="up"'
