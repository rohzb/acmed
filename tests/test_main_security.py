import io
import json
from types import SimpleNamespace

import pytest

from acmed.errors import AcmeProblemError
from acmed.main import _base_url, _read_body, build_wsgi_app


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
