import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acmed.errors import AcmeProblemError
from acmed.main import (
    _base_url,
    _ensure_listener_certificate,
    _read_body,
    _respond_json,
    build_runtime,
    build_wsgi_app,
)


def _make_cfg(*, external_base_url=None, trust_forwarded_headers=False, trusted_proxy_cidrs=None):
    return SimpleNamespace(
        server=SimpleNamespace(
            external_base_url=external_base_url,
            trust_forwarded_headers=trust_forwarded_headers,
            trusted_proxy_cidrs=trusted_proxy_cidrs,
        ),
        limits=SimpleNamespace(max_request_body_bytes=8),
    )


def test_read_body_rejects_large_payload():
    environ = {
        "CONTENT_LENGTH": "9",
        "wsgi.input": io.BytesIO(b"123456789"),
    }
    with pytest.raises(AcmeProblemError) as exc:
        _read_body(environ, max_bytes=8)
    assert exc.value.http_status == 413


def test_base_url_prefers_explicit_external_base_url():
    cfg = _make_cfg(external_base_url="https://public.example.org")
    environ = {
        "wsgi.url_scheme": "http",
        "HTTP_HOST": "internal.local:8443",
        "HTTP_X_FORWARDED_PROTO": "https",
        "HTTP_X_FORWARDED_HOST": "forwarded.example.org",
        "REMOTE_ADDR": "10.0.0.1",
    }
    assert _base_url(environ, cfg) == "https://public.example.org"


def test_base_url_ignores_forwarded_headers_when_disabled():
    cfg = _make_cfg(trust_forwarded_headers=False, trusted_proxy_cidrs=["10.0.0.0/24"])
    environ = {
        "wsgi.url_scheme": "http",
        "HTTP_HOST": "internal.local:8443",
        "HTTP_X_FORWARDED_PROTO": "https",
        "HTTP_X_FORWARDED_HOST": "forwarded.example.org",
        "REMOTE_ADDR": "10.0.0.2",
    }
    assert _base_url(environ, cfg) == "http://internal.local:8443"


def test_base_url_uses_forwarded_headers_only_for_trusted_proxy():
    cfg = _make_cfg(trust_forwarded_headers=True, trusted_proxy_cidrs=["10.0.0.0/24"])
    trusted = {
        "wsgi.url_scheme": "http",
        "HTTP_HOST": "internal.local:8443",
        "HTTP_X_FORWARDED_PROTO": "https",
        "HTTP_X_FORWARDED_HOST": "forwarded.example.org",
        "REMOTE_ADDR": "10.0.0.3",
    }
    assert _base_url(trusted, cfg) == "https://forwarded.example.org"

    untrusted = dict(trusted)
    untrusted["REMOTE_ADDR"] = "192.168.1.10"
    assert _base_url(untrusted, cfg) == "http://internal.local:8443"


def test_wsgi_acme_unhandled_error_is_sanitized():
    runtime = SimpleNamespace(
        config=_make_cfg(),
        storage=SimpleNamespace(create_nonce=lambda: "nonce-1"),
        api_service=SimpleNamespace(),
        auth_service=SimpleNamespace(),
        worker=SimpleNamespace(),
        acme_service=SimpleNamespace(
            directory=lambda base_url: (_ for _ in ()).throw(RuntimeError("boom secret detail"))
        ),
    )
    app = build_wsgi_app(runtime)

    status_holder: list[str] = []
    headers_holder: list[tuple[str, str]] = []

    def start_response(status, headers):
        status_holder.append(status)
        headers_holder.extend(headers)

    body = b"".join(
        app(
            {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": "/acme/directory",
                "wsgi.url_scheme": "https",
                "SERVER_NAME": "127.0.0.1",
                "SERVER_PORT": "8443",
            },
            start_response,
        )
    )
    parsed = json.loads(body.decode("utf-8"))
    assert status_holder[0].startswith("500")
    assert parsed["type"] == "urn:ietf:params:acme:error:serverInternal"
    assert "boom" not in parsed["detail"]


def test_respond_json_uses_compact_encoding_for_client_compatibility():
    status_holder = []
    headers_holder = []

    def start_response(status, headers):
        status_holder.append(status)
        headers_holder.extend(headers)

    body = b"".join(
        _respond_json(
            start_response,
            200,
            {"status": "valid", "certificate": "http://example/cert"},
            {"Content-Type": "application/json"},
        )
    )
    rendered = body.decode("utf-8")
    assert '"status":"valid"' in rendered
    assert '"certificate":"http://example/cert"' in rendered


def test_listener_certificate_bootstrap_uses_worker_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ACMED_TEST_TOKEN", "secret")
    cert_path = tmp_path / "tls" / "fullchain.pem"
    key_path = tmp_path / "tls" / "privkey.pem"
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        f"""
server:
  host: 127.0.0.1
  port: 8443
  tls_enabled: false
  development_mode: false
  extra_listeners:
    - host: 127.0.0.1
      port: 9443
      tls_enabled: true
      tls_cert_file: {cert_path}
      tls_key_file: {key_path}
  listener_certificate:
    enabled: true
    domains: [host1.lab.example.org]
    timeout_seconds: 10

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

storage:
  sqlite_path: {tmp_path / 'acmed.db'}
  artifacts_root: {tmp_path / 'orders'}

workers:
  poll_interval_seconds: 1

issuers:
  - name: mock
    type: mock

proof_handlers:
  - name: no-proof
    type: none

authorizers:
  - name: loopback
    type: source_subnet
    source_subnets: [127.0.0.0/8]

policies:
  - name: listener
    requester_match:
      authorizers: [loopback]
    allowed_domains:
      - syntax: exact
        value: host1.lab.example.org
    allowed_issuers: [mock]
    proof_handler: no-proof
""",
        encoding="utf-8",
    )
    runtime = build_runtime(str(config_path))
    runtime.worker.start()
    try:
        _ensure_listener_certificate(runtime)
    finally:
        runtime.worker.stop()
        runtime.storage.close()

    assert "BEGIN CERTIFICATE" in cert_path.read_text(encoding="utf-8")
    assert "BEGIN PRIVATE KEY" in key_path.read_text(encoding="utf-8")
