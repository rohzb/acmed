"""Runtime entrypoint for acmed.

This module wires configuration, storage, worker loop, and a small WSGI app.
"""

from __future__ import annotations

import json
import ipaddress
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
from .errors import AcmedError, AcmeProblemError
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
    """Build configured runtime services from a YAML configuration file.

    Args:
        config_path: Filesystem path to the acmed configuration YAML.

    Returns:
        Initialized runtime dependency container.
    """
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
    """Create a WSGI application callable bound to runtime services.

    Args:
        runtime: Runtime dependency container with configured services.

    Returns:
        WSGI callable that handles acmed API and ACME routes.
    """
    def app(environ: dict[str, Any], start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "")
        base_url = _base_url(environ, runtime.config)
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
                req = _parse_signed_request(environ, runtime.config)
                return _respond_json(start_response, *runtime.acme_service.new_account(req, base_url=base_url))

            if path.startswith("/acme/account/") and path.endswith("/orders") and method == "POST":
                account_id = path.split("/")[3]
                req = _parse_signed_request(environ, runtime.config)
                return _respond_json(start_response, *runtime.acme_service.list_account_orders(req, account_id, base_url))

            if path.startswith("/acme/account/") and method == "POST":
                account_id = path.split("/")[3]
                req = _parse_signed_request(environ, runtime.config)
                return _respond_json(start_response, *runtime.acme_service.get_account(req, account_id, base_url))

            if method == "POST" and path == "/acme/new-order":
                req = _parse_signed_request(environ, runtime.config)
                return _respond_json(start_response, *runtime.acme_service.new_order(req, base_url=base_url))

            if path.startswith("/acme/order/") and path.endswith("/finalize") and method == "POST":
                order_id = path.split("/")[3]
                req = _parse_signed_request(environ, runtime.config)
                return _respond_json(start_response, *runtime.acme_service.finalize_order(req, order_id, base_url))

            if path.startswith("/acme/order/") and method == "POST":
                order_id = path.split("/")[3]
                req = _parse_signed_request(environ, runtime.config)
                return _respond_json(start_response, *runtime.acme_service.get_order(req, order_id, base_url))

            if path.startswith("/acme/authz/") and method == "POST":
                authz_id = path.split("/")[3]
                req = _parse_signed_request(environ, runtime.config)
                return _respond_json(start_response, *runtime.acme_service.get_authorization(req, authz_id, base_url))

            if path.startswith("/acme/challenge/") and method == "POST":
                challenge_id = path.split("/")[3]
                req = _parse_signed_request(environ, runtime.config)
                if req.payload_raw.strip():
                    return _respond_json(
                        start_response,
                        *runtime.acme_service.acknowledge_challenge(req, challenge_id, base_url),
                    )
                return _respond_json(start_response, *runtime.acme_service.get_challenge(req, challenge_id, base_url))

            if path.startswith("/acme/cert/") and method == "POST":
                order_id = path.split("/")[3]
                req = _parse_signed_request(environ, runtime.config)
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
        except Exception:  # noqa: BLE001
            if path.startswith("/acme/"):
                return _respond_json(
                    start_response,
                    500,
                    {
                        "type": "urn:ietf:params:acme:error:serverInternal",
                        "detail": "internal ACME server error",
                    },
                    {"Content-Type": "application/problem+json", "Replay-Nonce": runtime.storage.create_nonce()},
                )
            return _respond_json(
                start_response,
                500,
                {"error": "internal_error", "message": "internal server error"},
                {"Content-Type": "application/json"},
            )

    return app


def run(config_path: str) -> None:
    """Run the acmed process with worker loop and WSGI server.

    Args:
        config_path: Filesystem path to the acmed configuration YAML.

    Returns:
        `None` after the process exits.
    """
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


def _parse_signed_request(environ: dict[str, Any], config: AppConfig) -> SignedAcmeRequest:
    """Parse and verify incoming ACME JWS request."""
    body = _read_body(environ, config.limits.max_request_body_bytes)
    base_url = _base_url(environ, config)
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


def _read_body(environ: dict[str, Any], max_bytes: int) -> bytes:
    """Read request body from WSGI input stream."""
    raw_length = environ.get("CONTENT_LENGTH") or "0"
    try:
        length = int(raw_length)
    except ValueError as exc:
        raise AcmeProblemError("malformed", "invalid Content-Length header") from exc
    if length < 0:
        raise AcmeProblemError("malformed", "invalid Content-Length header")
    if length > max_bytes:
        raise AcmeProblemError("malformed", "request body exceeds configured limit", http_status=413)
    return environ["wsgi.input"].read(length)


def _base_url(environ: dict[str, Any], config: AppConfig) -> str:
    """Build absolute base URL from forwarded or server headers."""
    if config.server.external_base_url:
        return config.server.external_base_url

    trust_forwarded = bool(config.server.trust_forwarded_headers) and _is_trusted_proxy_request(environ, config)
    scheme = environ.get("wsgi.url_scheme", "https")
    host = environ.get("HTTP_HOST")
    if trust_forwarded:
        scheme = environ.get("HTTP_X_FORWARDED_PROTO") or scheme
        host = environ.get("HTTP_X_FORWARDED_HOST") or host
    if host:
        return f"{scheme}://{host}"
    return f"{scheme}://{environ.get('SERVER_NAME')}:{environ.get('SERVER_PORT')}"


def _is_trusted_proxy_request(environ: dict[str, Any], config: AppConfig) -> bool:
    """Return whether the direct peer IP is within configured trusted proxy CIDRs."""
    remote_addr = environ.get("REMOTE_ADDR")
    if not isinstance(remote_addr, str) or not remote_addr.strip():
        return False
    try:
        remote_ip = ipaddress.ip_address(remote_addr.strip())
    except ValueError:
        return False
    for cidr in config.server.trusted_proxy_cidrs or []:
        if remote_ip in ipaddress.ip_network(cidr, strict=False):
            return True
    return False


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
        413: "Payload Too Large",
        429: "Too Many Requests",
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
