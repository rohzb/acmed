"""Runtime entrypoint for acmed.

This module wires configuration, storage, worker loop, and a small WSGI app.
"""

from __future__ import annotations

import json
import signal
import sys
from dataclasses import dataclass
from types import FrameType
from typing import Any
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from .acme_api import AcmeApiService, SignedAcmeRequest
from .acme_jws import parse_and_verify_acme_jws
from .api import ApiService
from .auth import AuthService
from .config import AppConfig, load_config
from .errors import AcmedError
from .storage import Storage
from .worker import Worker


@dataclass(slots=True)
class AppRuntime:
    """Constructed runtime container for app dependencies."""
    config: AppConfig
    storage: Storage
    worker: Worker
    auth_service: AuthService
    api_service: ApiService
    acme_service: AcmeApiService


def build_runtime(config_path: str) -> AppRuntime:
    """Build configured runtime services from YAML configuration path."""
    config = load_config(config_path)
    storage = Storage(config.storage.sqlite_path, config.storage.artifacts_root)
    auth_service = AuthService(config)
    api_service = ApiService(storage=storage, auth_service=auth_service)
    acme_service = AcmeApiService(config=config, storage=storage)
    worker = Worker(config=config, storage=storage)
    return AppRuntime(
        config=config,
        storage=storage,
        worker=worker,
        auth_service=auth_service,
        api_service=api_service,
        acme_service=acme_service,
    )


def build_wsgi_app(runtime: AppRuntime):
    """Create WSGI application callable bound to runtime services."""
    def app(environ: dict[str, Any], start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "")
        base_url = _base_url(environ)
        environ["acmed.storage"] = runtime.storage
        try:
            if method == "GET" and path == "/healthz":
                return _respond_json(start_response, *runtime.api_service.health())

            if method == "GET" and path == "/api/v1/admin/orders":
                query = parse_qs(environ.get("QUERY_STRING", ""))
                limit = int(query.get("limit", ["100"])[0])
                bearer = _bearer_token(environ.get("HTTP_AUTHORIZATION"))
                return _respond_json(start_response, *runtime.api_service.list_admin_orders(bearer, limit=limit))

            if method == "GET" and path == "/acme/directory":
                return _respond_json(start_response, *runtime.acme_service.directory(base_url=base_url))

            if method in {"HEAD", "GET"} and path == "/acme/new-nonce":
                status, body, headers = runtime.acme_service.new_nonce()
                return _respond_json(start_response, status, body, headers, include_body=(method != "HEAD"))

            if method == "POST" and path == "/acme/new-account":
                req = _parse_signed_request(environ)
                return _respond_json(start_response, *runtime.acme_service.new_account(req, base_url=base_url))

            if path.startswith("/acme/account/") and path.endswith("/orders") and method == "POST":
                account_id = path.split("/")[3]
                req = _parse_signed_request(environ)
                return _respond_json(start_response, *runtime.acme_service.list_account_orders(req, account_id, base_url))

            if path.startswith("/acme/account/") and method == "POST":
                account_id = path.split("/")[3]
                req = _parse_signed_request(environ)
                return _respond_json(start_response, *runtime.acme_service.get_account(req, account_id, base_url))

            if method == "POST" and path == "/acme/new-order":
                req = _parse_signed_request(environ)
                return _respond_json(start_response, *runtime.acme_service.new_order(req, base_url=base_url))

            if path.startswith("/acme/order/") and path.endswith("/finalize") and method == "POST":
                order_id = path.split("/")[3]
                req = _parse_signed_request(environ)
                return _respond_json(start_response, *runtime.acme_service.finalize_order(req, order_id, base_url))

            if path.startswith("/acme/order/") and method == "POST":
                order_id = path.split("/")[3]
                req = _parse_signed_request(environ)
                return _respond_json(start_response, *runtime.acme_service.get_order(req, order_id, base_url))

            if path.startswith("/acme/authz/") and method == "POST":
                authz_id = path.split("/")[3]
                req = _parse_signed_request(environ)
                return _respond_json(start_response, *runtime.acme_service.get_authorization(req, authz_id, base_url))

            if path.startswith("/acme/challenge/") and method == "POST":
                challenge_id = path.split("/")[3]
                req = _parse_signed_request(environ)
                if req.payload_raw.strip():
                    return _respond_json(
                        start_response,
                        *runtime.acme_service.acknowledge_challenge(req, challenge_id, base_url),
                    )
                return _respond_json(start_response, *runtime.acme_service.get_challenge(req, challenge_id, base_url))

            if path.startswith("/acme/cert/") and method == "POST":
                order_id = path.split("/")[3]
                req = _parse_signed_request(environ)
                status, text_body, headers = runtime.acme_service.get_certificate(req, order_id)
                return _respond_text(start_response, status, text_body, headers)

            return _respond_json(start_response, 404, {"error": "not found"}, {"Content-Type": "application/json"})
        except AcmedError as exc:
            if path.startswith("/acme/"):
                problem = {
                    "type": f"urn:ietf:params:acme:error:{exc.code}",
                    "detail": exc.message,
                }
                return _respond_json(
                    start_response,
                    exc.http_status,
                    problem,
                    {"Content-Type": "application/problem+json", "Replay-Nonce": runtime.storage.create_nonce()},
                )
            return _respond_json(
                start_response,
                exc.http_status,
                {"error": exc.code, "message": exc.message},
                {"Content-Type": "application/json"},
            )
        except Exception as exc:  # noqa: BLE001
            return _respond_json(
                start_response,
                500,
                {"error": "internal_error", "message": str(exc)},
                {"Content-Type": "application/json"},
            )

    return app


def run(config_path: str) -> None:
    """Run ACME service process with worker loop and WSGI server."""
    runtime = build_runtime(config_path)
    runtime.worker.start()

    should_stop = {"value": False}

    def _handle_signal(_sig: int, _frame: FrameType | None) -> None:
        should_stop["value"] = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    app = build_wsgi_app(runtime)
    with make_server(runtime.config.server.host, runtime.config.server.port, app) as server:
        server.timeout = 1
        while not should_stop["value"]:
            server.handle_request()

    runtime.worker.stop()
    runtime.storage.close()


def _parse_signed_request(environ: dict[str, Any]) -> SignedAcmeRequest:
    """Parse and verify incoming ACME JWS request."""
    body = _read_body(environ)
    base_url = _base_url(environ)
    expected_url = f"{base_url}{environ.get('PATH_INFO', '')}"

    def _resolve_account_jwk(kid: str) -> dict[str, Any] | None:
        marker = "/acme/account/"
        if marker not in kid:
            return None
        account_id = kid.rsplit(marker, 1)[1]
        runtime_storage = environ.get("acmed.storage")
        if runtime_storage is None:
            return None
        return runtime_storage.get_acme_account_jwk(account_id)

    verified = parse_and_verify_acme_jws(body=body, key_resolver=_resolve_account_jwk, expected_url=expected_url)
    return SignedAcmeRequest(
        url=verified.url,
        nonce=verified.nonce,
        kid=verified.kid,
        jwk=verified.jwk,
        jwk_thumbprint=verified.jwk_thumbprint,
        payload=verified.payload_obj,
        payload_raw=verified.payload_raw,
        request_ip=environ.get("REMOTE_ADDR"),
    )


def _read_body(environ: dict[str, Any]) -> bytes:
    """Read request body from WSGI input stream."""
    length = int(environ.get("CONTENT_LENGTH") or "0")
    return environ["wsgi.input"].read(length)


def _base_url(environ: dict[str, Any]) -> str:
    """Build absolute base URL from forwarded or server headers."""
    scheme = environ.get("HTTP_X_FORWARDED_PROTO") or environ.get("wsgi.url_scheme", "https")
    host = environ.get("HTTP_X_FORWARDED_HOST") or environ.get("HTTP_HOST")
    if host:
        return f"{scheme}://{host}"
    return f"{scheme}://{environ.get('SERVER_NAME')}:{environ.get('SERVER_PORT')}"


def _respond_json(
    start_response,
    status: int,
    body: dict[str, Any],
    headers: dict[str, str],
    include_body: bool = True,
):
    """Return JSON WSGI response body and headers."""
    payload = json.dumps(body).encode("utf-8") if include_body else b""
    header_list = list(headers.items()) + [("Content-Length", str(len(payload)))]
    start_response(f"{status} {_reason_phrase(status)}", header_list)
    return [payload]


def _respond_text(start_response, status: int, body: str, headers: dict[str, str]):
    """Return text WSGI response body and headers."""
    payload = body.encode("utf-8")
    header_list = list(headers.items()) + [("Content-Length", str(len(payload)))]
    start_response(f"{status} {_reason_phrase(status)}", header_list)
    return [payload]


def _reason_phrase(status: int) -> str:
    """Map HTTP status code to short reason phrase."""
    return {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        500: "Internal Server Error",
    }.get(status, "OK")


def _bearer_token(header: str | None) -> str | None:
    """Extract bearer token value from Authorization header."""
    if not header:
        return None
    prefix = "Bearer "
    if not header.startswith(prefix):
        return None
    return header[len(prefix) :].strip()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m acmed.main <config.yml>")
        raise SystemExit(2)
    run(sys.argv[1])
