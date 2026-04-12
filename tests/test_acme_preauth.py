from pathlib import Path

import pytest

from acmed.acme_api import AcmeApiService, SignedAcmeRequest
from acmed.config import load_config
from acmed.errors import AcmeProblemError
from acmed.storage import Storage


def _write_cfg(tmp_path: Path) -> Path:
    cfg = f"""
server:
  host: 127.0.0.1
  port: 8443
  tls_enabled: true

identity:
  api_tokens:
    enabled: true
    tokens:
      - token_id: t1
        subject: acmed-admin
        secret_env: ACMED_TEST_TOKEN
        roles: [requester]
  mtls:
    enabled: false

access:
  admin_subjects: [acmed-admin]

acme:
  require_eab: false
  supported_challenge_types: [http-01]

storage:
  sqlite_path: {tmp_path / 'acmed.db'}
  artifacts_root: {tmp_path / 'orders'}

issuers:
  - name: mock
    type: mock

proof_handlers:
  - name: no-proof
    type: none

authorizers:
  - name: subnet-lab
    type: source_subnet
    source_subnets: [10.0.0.0/24]

policies:
  - name: p1
    requester_match:
      authorizers: [subnet-lab]
    allowed_domains:
      - syntax: exact
        value: host1.lab.example.org
    allowed_issuers: [mock]
    proof_handler: no-proof
"""
    path = tmp_path / "cfg.yml"
    path.write_text(cfg, encoding="utf-8")
    return path


def _seed_account(storage: Storage) -> str:
    account = storage.get_or_create_acme_account(
        jwk_thumbprint="tp-1",
        jwk={"kty": "EC", "crv": "P-256", "x": "AA", "y": "BB"},
        contact=[],
        eab_kid=None,
    )
    return str(account["id"])


def test_new_order_rejects_when_preauth_authorizer_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ACMED_TEST_TOKEN", "secret")
    cfg = load_config(_write_cfg(tmp_path))
    storage = Storage(cfg.storage.sqlite_path, cfg.storage.artifacts_root)
    service = AcmeApiService(cfg, storage)

    account_id = _seed_account(storage)
    req = SignedAcmeRequest(
        url="https://acme.example.org/acme/new-order",
        nonce=storage.create_nonce(),
        payload={"identifiers": [{"type": "dns", "value": "host1.lab.example.org"}]},
        payload_raw=b'{"identifiers":[]}',
        kid=f"https://acme.example.org/acme/account/{account_id}",
        request_ip="192.168.10.10",
    )

    with pytest.raises(AcmeProblemError) as exc:
        service.new_order(req, "https://acme.example.org")
    assert exc.value.code == "rejectedIdentifier"


def test_new_order_accepts_when_preauth_authorizer_matches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ACMED_TEST_TOKEN", "secret")
    cfg = load_config(_write_cfg(tmp_path))
    storage = Storage(cfg.storage.sqlite_path, cfg.storage.artifacts_root)
    service = AcmeApiService(cfg, storage)

    account_id = _seed_account(storage)
    req = SignedAcmeRequest(
        url="https://acme.example.org/acme/new-order",
        nonce=storage.create_nonce(),
        payload={"identifiers": [{"type": "dns", "value": "host1.lab.example.org"}]},
        payload_raw=b'{"identifiers":[]}',
        kid=f"https://acme.example.org/acme/account/{account_id}",
        request_ip="10.0.0.20",
    )

    status, body, _headers = service.new_order(req, "https://acme.example.org")
    assert status == 201
    assert body["status"] in {"pending", "ready"}
