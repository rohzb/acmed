"""ACME-first API handlers mapped onto the broker core."""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import ssl
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.x509 import ObjectIdentifier
from cryptography.x509.oid import NameOID

from .acme_jws import verify_external_account_binding
from .authorizers import AuthorizerInput, AuthorizerService
from .config import AppConfig
from .errors import AcmeProblemError, AuthorizationError, NotFoundError
from .models import CsrSource, OrderRequest, OrderStatus, PrivateKeyPolicy
from .policy import resolve_policy
from .storage import Storage
from .utils import normalize_dns_name, normalize_dns_names, utc_iso


@dataclass(slots=True)
class SignedAcmeRequest:
    """Verified ACME request envelope extracted from JOSE JWS."""

    url: str
    nonce: str
    payload: dict[str, Any]
    payload_raw: bytes
    kid: str | None = None
    jwk: dict[str, Any] | None = None
    jwk_thumbprint: str | None = None
    request_ip: str | None = None


class AcmeApiService:
    """Transport-agnostic ACME handlers."""

    def __init__(self, config: AppConfig, storage: Storage) -> None:
        self._config = config
        self._storage = storage
        self._authorizers = AuthorizerService(config)

    def directory(self, base_url: str) -> tuple[int, dict[str, Any], dict[str, str]]:
        body = {
            "newNonce": f"{base_url}/acme/new-nonce",
            "newAccount": f"{base_url}/acme/new-account",
            "newOrder": f"{base_url}/acme/new-order",
            "meta": {"externalAccountRequired": self._config.acme.require_eab},
        }
        return 200, body, {"Content-Type": "application/json"}

    def new_nonce(self) -> tuple[int, dict[str, Any], dict[str, str]]:
        nonce = self._storage.create_nonce()
        return 200, {}, {"Replay-Nonce": nonce}

    def new_account(self, req: SignedAcmeRequest, base_url: str) -> tuple[int, dict[str, Any], dict[str, str]]:
        self._validate_signed_request(req, require_jwk=True)

        if req.jwk is None or req.jwk_thumbprint is None:
            raise AcmeProblemError("badPublicKey", "newAccount requires JWK")

        only_existing = bool(req.payload.get("onlyReturnExisting", False))
        existing = self._storage.find_acme_account_by_thumbprint(req.jwk_thumbprint)
        if only_existing:
            if existing is None:
                raise AcmeProblemError("accountDoesNotExist", "account does not exist")
            account_id = existing["id"]
            headers = {
                "Replay-Nonce": self._storage.create_nonce(),
                "Location": f"{base_url}/acme/account/{account_id}",
            }
            return 200, self._account_object(account_id, existing, base_url), headers

        external_binding = req.payload.get("externalAccountBinding")
        eab_kid: str | None = None
        if self._config.acme.require_eab:
            if not isinstance(external_binding, dict):
                raise AcmeProblemError("externalAccountRequired", "externalAccountBinding is required")
            eab_kid = verify_external_account_binding(
                external_account_binding=external_binding,
                expected_url=req.url,
                account_jwk=req.jwk,
                secret_lookup=self._lookup_eab_secret,
            )

        contact = req.payload.get("contact", [])
        if not isinstance(contact, list):
            raise AcmeProblemError("malformed", "contact must be a list")

        account = self._storage.get_or_create_acme_account(
            jwk_thumbprint=req.jwk_thumbprint,
            jwk=req.jwk,
            contact=contact,
            eab_kid=eab_kid,
        )
        account_id = account["id"]
        headers = {
            "Replay-Nonce": self._storage.create_nonce(),
            "Location": f"{base_url}/acme/account/{account_id}",
        }
        status = 201 if existing is None else 200
        return status, self._account_object(account_id, account, base_url), headers

    def get_account(self, req: SignedAcmeRequest, account_id: str, base_url: str) -> tuple[int, dict[str, Any], dict[str, str]]:
        self._validate_signed_request(req, expected_account_id=account_id, require_kid=True)
        account = self._storage.get_acme_account(account_id)
        return 200, self._account_object(account_id, account, base_url), {"Replay-Nonce": self._storage.create_nonce()}

    def list_account_orders(
        self,
        req: SignedAcmeRequest,
        account_id: str,
        base_url: str,
    ) -> tuple[int, dict[str, Any], dict[str, str]]:
        self._validate_signed_request(req, expected_account_id=account_id, require_kid=True, require_post_as_get=True)
        order_ids = self._storage.list_account_order_ids(account_id)
        orders = [f"{base_url}/acme/order/{order_id}" for order_id in order_ids]
        return 200, {"orders": orders}, {"Replay-Nonce": self._storage.create_nonce()}

    def new_order(self, req: SignedAcmeRequest, base_url: str) -> tuple[int, dict[str, Any], dict[str, str]]:
        account_id = self._require_account_from_kid(req)
        identifiers = req.payload.get("identifiers", [])
        if not isinstance(identifiers, list) or not identifiers:
            raise AcmeProblemError("malformed", "identifiers required")

        dns_names: list[str] = []
        for item in identifiers:
            if not isinstance(item, dict) or item.get("type") != "dns":
                raise AcmeProblemError("rejectedIdentifier", "unsupported identifier type")
            value = normalize_dns_name(str(item.get("value", "")))
            if value.startswith("*.") and not self._config.acme.allow_wildcards:
                raise AcmeProblemError("rejectedIdentifier", "wildcards are not enabled")
            dns_names.append(value)

        normalized_dns = normalize_dns_names(dns_names)
        if len(normalized_dns) > self._config.limits.max_dns_names_per_order:
            raise AcmeProblemError("malformed", "too many dns names")

        csr_source = CsrSource.SERVICE_GENERATED
        request_ip = req.request_ip
        allowed_authorizers = self._authorizers.allowed_authorizers(
            AuthorizerInput(
                requester_id=account_id,
                request_ip=request_ip,
                dns_names=normalized_dns,
            )
        )
        try:
            resolved = resolve_policy(
                config=self._config,
                requester_authorizers=allowed_authorizers,
                dns_names=normalized_dns,
                requested_issuer=None,
                csr_source=csr_source,
                enforce_authorizers=True,
            )
        except AuthorizationError as exc:
            raise AcmeProblemError(
                "rejectedIdentifier",
                "request identifiers are not authorized by policy",
                http_status=403,
            ) from exc

        order_request = OrderRequest(
            requester_id=account_id,
            requester_ip=request_ip,
            request_source="acme",
            dns_names=normalized_dns,
            common_name=normalized_dns[0],
            issuer_name=resolved.issuer_name,
            csr_pem=None,
            idempotency_key=req.payload.get("idempotencyKey"),
            not_before=_parse_optional_time(req.payload.get("notBefore")),
            not_after=_parse_optional_time(req.payload.get("notAfter")),
        )
        order, created = self._storage.create_order(
            request=order_request,
            issuer_name=resolved.issuer_name,
            proof_handler_name=resolved.proof_handler_name,
            challenge_validation_mode=resolved.policy.challenge_validation_mode,
            private_key_policy=PrivateKeyPolicy.SERVICE_GENERATED,
            max_retries=self._config.orders.max_retries,
            ttl_seconds=self._config.orders.default_ttl_seconds,
        )
        self._storage.add_acme_account_order_link(account_id, order.id)

        auth_urls: list[str] = []
        existing_authzs = self._storage.list_acme_authorizations_for_order(order.id)
        if not existing_authzs:
            for name in order.dns_names:
                auth_id = self._storage.create_acme_authorization(
                    order_id=order.id,
                    identifier_value=name,
                )
                for challenge_type in self._config.acme.supported_challenge_types:
                    if name.startswith("*.") and challenge_type == "http-01":
                        continue
                    self._storage.create_acme_challenge(auth_id, challenge_type)
                auth_urls.append(f"{base_url}/acme/authz/{auth_id}")
        else:
            auth_urls = [f"{base_url}/acme/authz/{item['id']}" for item in existing_authzs]

        status_code = 201 if created else 200
        headers = {
            "Replay-Nonce": self._storage.create_nonce(),
            "Location": f"{base_url}/acme/order/{order.id}",
        }
        return status_code, self._order_object(order.id, auth_urls, base_url), headers

    def get_order(self, req: SignedAcmeRequest, order_id: str, base_url: str) -> tuple[int, dict[str, Any], dict[str, str]]:
        account_id = self._require_account_from_kid(req, require_post_as_get=True)
        self._require_order_ownership(account_id, order_id)
        authzs = self._storage.list_acme_authorizations_for_order(order_id)
        auth_urls = [f"{base_url}/acme/authz/{item['id']}" for item in authzs]
        return 200, self._order_object(order_id, auth_urls, base_url), {"Replay-Nonce": self._storage.create_nonce()}

    def get_authorization(
        self,
        req: SignedAcmeRequest,
        authorization_id: str,
        base_url: str,
    ) -> tuple[int, dict[str, Any], dict[str, str]]:
        account_id = self._require_account_from_kid(req, require_post_as_get=True)
        order_id = self._storage.get_order_id_for_authorization(authorization_id)
        self._require_order_ownership(account_id, order_id)

        authz = next(
            (item for item in self._storage.list_acme_authorizations_for_order(order_id) if item["id"] == authorization_id),
            None,
        )
        if authz is None:
            raise NotFoundError(f"authorization {authorization_id} not found")

        challenges = self._storage.list_acme_challenges_for_authorization(authorization_id)
        challenge_objs = [self._challenge_object(item["id"], item, base_url) for item in challenges]
        body = {
            "identifier": {"type": authz["identifier_type"], "value": authz["identifier_value"]},
            "status": authz["status"],
            "expires": authz["expires_at"],
            "wildcard": bool(authz["wildcard"]),
            "challenges": challenge_objs,
        }
        return 200, body, {"Replay-Nonce": self._storage.create_nonce()}

    def get_challenge(self, req: SignedAcmeRequest, challenge_id: str, base_url: str) -> tuple[int, dict[str, Any], dict[str, str]]:
        account_id = self._require_account_from_kid(req, require_post_as_get=True)
        order_id = self._storage.get_order_id_for_challenge(challenge_id)
        self._require_order_ownership(account_id, order_id)
        challenge = self._storage.get_acme_challenge(challenge_id)
        return 200, self._challenge_object(challenge_id, challenge, base_url), self._challenge_headers(
            base_url=base_url,
            authorization_id=str(challenge["authorization_id"]),
        )

    def acknowledge_challenge(
        self,
        req: SignedAcmeRequest,
        challenge_id: str,
        base_url: str,
    ) -> tuple[int, dict[str, Any], dict[str, str]]:
        account_id = self._require_account_from_kid(req)
        order_id = self._storage.get_order_id_for_challenge(challenge_id)
        self._require_order_ownership(account_id, order_id)

        context = self._storage.get_challenge_validation_context(challenge_id)
        challenge_status = context["challenge_status"]
        if challenge_status in {"valid", "invalid"}:
            challenge = self._storage.get_acme_challenge(challenge_id)
            return 200, self._challenge_object(challenge_id, challenge, base_url), self._challenge_headers(
                base_url=base_url,
                authorization_id=str(challenge["authorization_id"]),
            )

        if self._is_trusted_challenge_bypass_enabled(order_id):
            self._storage.set_acme_challenge_status(challenge_id, status="valid")
        else:
            valid, error_code, error_detail = self._validate_challenge(context)
            if valid:
                self._storage.set_acme_challenge_status(challenge_id, status="valid")
            else:
                self._storage.set_acme_challenge_status(
                    challenge_id,
                    status="invalid",
                    error_code=error_code,
                    error_detail=error_detail,
                )

        challenge = self._storage.get_acme_challenge(challenge_id)
        return 200, self._challenge_object(challenge_id, challenge, base_url), self._challenge_headers(
            base_url=base_url,
            authorization_id=str(challenge["authorization_id"]),
        )

    def finalize_order(
        self,
        req: SignedAcmeRequest,
        order_id: str,
        base_url: str,
    ) -> tuple[int, dict[str, Any], dict[str, str]]:
        account_id = self._require_account_from_kid(req)
        self._require_order_ownership(account_id, order_id)

        csr_b64 = req.payload.get("csr")
        if not isinstance(csr_b64, str) or not csr_b64.strip():
            raise AcmeProblemError("badCSR", "csr is required for finalize")

        csr = _parse_csr(csr_b64)
        requested = set(self._storage.get_order(order_id).dns_names)
        csr_names = _csr_dns_names(csr)
        if requested != csr_names:
            raise AcmeProblemError("badCSR", "CSR names must exactly match order identifiers")

        authzs = self._storage.list_acme_authorizations_for_order(order_id)
        if not authzs or any(item["status"] != "valid" for item in authzs):
            raise AcmeProblemError("orderNotReady", "order is not ready for finalize")

        self._storage.set_order_finalize_requested(order_id, enabled=True)

        body = self._order_object(
            order_id=order_id,
            auth_urls=[f"{base_url}/acme/authz/{item['id']}" for item in authzs],
            base_url=base_url,
        )
        return 200, body, {"Replay-Nonce": self._storage.create_nonce()}

    def get_certificate(
        self,
        req: SignedAcmeRequest,
        order_id: str,
    ) -> tuple[int, str, dict[str, str]]:
        account_id = self._require_account_from_kid(req, require_post_as_get=True)
        self._require_order_ownership(account_id, order_id)

        order = self._storage.get_order(order_id)
        if order.status != OrderStatus.ISSUED:
            raise AcmeProblemError("orderNotReady", "certificate not available")

        certificate_path = Path(self._config.storage.artifacts_root) / order_id / "fullchain.pem"
        if not certificate_path.exists():
            raise NotFoundError("certificate artifact missing")
        content = certificate_path.read_text(encoding="utf-8")
        return 200, content, {
            "Content-Type": "application/pem-certificate-chain",
            "Replay-Nonce": self._storage.create_nonce(),
        }

    def _validate_signed_request(
        self,
        req: SignedAcmeRequest,
        expected_account_id: str | None = None,
        require_kid: bool = False,
        require_jwk: bool = False,
        require_post_as_get: bool = False,
    ) -> None:
        if not req.nonce or not self._storage.consume_nonce(req.nonce):
            raise AcmeProblemError("badNonce", "missing or stale nonce")
        if not req.url:
            raise AcmeProblemError("malformed", "missing request URL")
        if require_kid and not req.kid:
            raise AcmeProblemError("malformed", "kid is required")
        if require_jwk and req.jwk is None:
            raise AcmeProblemError("malformed", "jwk is required")
        if require_post_as_get and req.payload_raw.strip():
            raise AcmeProblemError("malformed", "POST-as-GET requests require empty payload")

        if expected_account_id:
            account_id = self._account_id_from_kid(req.kid)
            if account_id != expected_account_id:
                raise AuthorizationError("account ownership mismatch")

    def _require_account_from_kid(self, req: SignedAcmeRequest, require_post_as_get: bool = False) -> str:
        self._validate_signed_request(req, require_kid=True, require_post_as_get=require_post_as_get)
        account_id = self._account_id_from_kid(req.kid)
        if account_id is None:
            raise AcmeProblemError("malformed", "invalid account kid")
        self._storage.get_acme_account(account_id)
        return account_id

    def _account_id_from_kid(self, kid: str | None) -> str | None:
        if not kid:
            return None
        marker = "/acme/account/"
        if marker not in kid:
            return None
        return kid.rsplit(marker, 1)[1]

    def _require_order_ownership(self, account_id: str, order_id: str) -> None:
        if not self._storage.account_owns_order(account_id, order_id):
            raise AuthorizationError("order ownership mismatch")

    def _account_object(self, account_id: str, account: dict[str, Any], base_url: str) -> dict[str, Any]:
        return {
            "status": account["status"],
            "contact": account.get("contact_json") and list(_json_load(account["contact_json"])) or [],
            "orders": f"{base_url}/acme/account/{account_id}/orders",
        }

    def _order_object(self, order_id: str, auth_urls: list[str], base_url: str) -> dict[str, Any]:
        order = self._storage.get_order(order_id)
        status = self._compute_order_status(order_id, order)
        body: dict[str, Any] = {
            "status": status,
            "identifiers": [{"type": "dns", "value": name} for name in order.dns_names],
            "authorizations": auth_urls,
            "finalize": f"{base_url}/acme/order/{order_id}/finalize",
            "expires": utc_iso(order.expires_at),
        }
        if status == "valid":
            body["certificate"] = f"{base_url}/acme/cert/{order_id}"
        if status == "invalid" and order.error_message:
            body["error"] = {"type": "urn:ietf:params:acme:error:serverInternal", "detail": order.error_message}
        return body

    def _challenge_object(self, challenge_id: str, challenge: dict[str, Any], base_url: str) -> dict[str, Any]:
        body = {
            "type": challenge["challenge_type"],
            "url": f"{base_url}/acme/challenge/{challenge_id}",
            "status": challenge["status"],
            "token": challenge["token"],
        }
        if challenge.get("validated_at"):
            body["validated"] = challenge["validated_at"]
        if challenge.get("error_code"):
            body["error"] = {
                "type": f"urn:ietf:params:acme:error:{challenge['error_code']}",
                "detail": challenge.get("error_detail") or "challenge failed",
            }
        return body

    def _challenge_headers(self, base_url: str, authorization_id: str) -> dict[str, str]:
        """Build ACME challenge response headers including required authz up-link."""
        return {
            "Replay-Nonce": self._storage.create_nonce(),
            "Link": f'<{base_url}/acme/authz/{authorization_id}>;rel="up"',
        }

    def _is_trusted_challenge_bypass_enabled(self, order_id: str) -> bool:
        """Return whether order policy allows trusted challenge auto-validation."""
        order = self._storage.get_order(order_id)
        return order.challenge_validation_mode == "trusted_bypass"

    def _lookup_eab_secret(self, kid: str) -> str | None:
        for credential in self._config.acme.eab_credentials or []:
            if credential.kid == kid:
                return os.environ.get(credential.secret_env)
        return None

    def _compute_order_status(self, order_id: str, order) -> str:
        authzs = self._storage.list_acme_authorizations_for_order(order_id)
        auth_statuses = {item["status"] for item in authzs}
        finalized = self._storage.is_order_finalize_requested(order_id)

        if order.status == OrderStatus.ISSUED:
            return "valid"
        if order.status in {OrderStatus.DENIED, OrderStatus.FAILED, OrderStatus.EXPIRED}:
            return "invalid"
        if "invalid" in auth_statuses:
            return "invalid"
        if authzs and auth_statuses == {"valid"}:
            return "processing" if finalized else "ready"
        return "pending"

    def _validate_challenge(self, context: dict[str, Any]) -> tuple[bool, str | None, str | None]:
        challenge_type = context["challenge_type"]
        if challenge_type == "http-01":
            return self._validate_http_01(context)
        if challenge_type == "dns-01":
            return self._validate_dns_01(context)
        if challenge_type == "tls-alpn-01":
            return self._validate_tls_alpn_01(context)
        return False, "malformed", f"unsupported challenge type: {challenge_type}"

    def _validate_http_01(self, context: dict[str, Any]) -> tuple[bool, str | None, str | None]:
        import urllib.request

        identifier = str(context["identifier_value"])
        token = str(context["token"])
        key_auth = self._key_authorization(token=token, thumbprint=str(context["jwk_thumbprint"]))
        challenge_url = f"http://{identifier}/.well-known/acme-challenge/{token}"
        try:
            with urllib.request.urlopen(challenge_url, timeout=5) as resp:
                body = resp.read(4096).decode("utf-8").strip()
        except Exception as exc:  # noqa: BLE001
            return False, "connection", f"http-01 fetch failed: {exc}"

        if body != key_auth:
            return False, "unauthorized", "http-01 key authorization mismatch"
        return True, None, None

    def _validate_dns_01(self, context: dict[str, Any]) -> tuple[bool, str | None, str | None]:
        identifier = str(context["identifier_value"])
        token = str(context["token"])
        thumbprint = str(context["jwk_thumbprint"])
        key_auth = self._key_authorization(token=token, thumbprint=thumbprint)
        expected_txt = _b64url_nopad(hashlib.sha256(key_auth.encode("utf-8")).digest())

        dns_name = identifier[2:] if identifier.startswith("*.") else identifier
        challenge_fqdn = f"_acme-challenge.{dns_name}"
        try:
            values = _query_txt_records(challenge_fqdn)
        except Exception as exc:  # noqa: BLE001
            return False, "connection", f"dns-01 TXT lookup failed: {exc}"

        if expected_txt not in values:
            return False, "unauthorized", "dns-01 TXT value mismatch"
        return True, None, None

    def _validate_tls_alpn_01(self, context: dict[str, Any]) -> tuple[bool, str | None, str | None]:
        identifier = str(context["identifier_value"])
        token = str(context["token"])
        thumbprint = str(context["jwk_thumbprint"])
        key_auth = self._key_authorization(token=token, thumbprint=thumbprint)
        expected_digest = hashlib.sha256(key_auth.encode("utf-8")).digest()
        oid = ObjectIdentifier("1.3.6.1.5.5.7.1.31")

        try:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            ssl_ctx.set_alpn_protocols(["acme-tls/1"])
            with socket.create_connection((identifier, 443), timeout=5) as sock:
                with ssl_ctx.wrap_socket(sock, server_hostname=identifier) as tls_sock:
                    selected = tls_sock.selected_alpn_protocol()
                    if selected != "acme-tls/1":
                        return False, "unauthorized", "tls-alpn-01 ALPN negotiation failed"
                    der = tls_sock.getpeercert(binary_form=True)
        except Exception as exc:  # noqa: BLE001
            return False, "connection", f"tls-alpn-01 connection failed: {exc}"

        try:
            cert = x509.load_der_x509_certificate(der)
            ext = cert.extensions.get_extension_for_oid(oid).value
            value = ext.value
        except Exception as exc:  # noqa: BLE001
            return False, "unauthorized", f"tls-alpn-01 acmeIdentifier extension missing: {exc}"

        if value == expected_digest:
            return True, None, None
        if len(value) == 34 and value[:2] == b"\x04\x20" and value[2:] == expected_digest:
            return True, None, None
        return False, "unauthorized", "tls-alpn-01 digest mismatch"

    def _key_authorization(self, token: str, thumbprint: str) -> str:
        return f"{token}.{thumbprint}"


def _json_load(value: str) -> Any:
    """Parse JSON text into Python object."""
    import json

    return json.loads(value)


def _parse_optional_time(value: str | None) -> datetime | None:
    """Parse optional RFC3339-like timestamp into datetime."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _decode_b64url(value: str) -> bytes:
    """Decode base64url string with implicit padding."""
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _b64url_nopad(value: bytes) -> str:
    """Encode bytes as unpadded base64url string."""
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _query_txt_records(name: str) -> set[str]:
    """Resolve TXT records for a name using dnspython, with nslookup fallback."""
    records: set[str] = set()
    try:
        import dns.resolver  # type: ignore

        answers = dns.resolver.resolve(name, "TXT")
        for item in answers:
            text = "".join(part.decode("utf-8") for part in item.strings)
            records.add(text)
        return records
    except Exception:
        pass

    try:
        completed = subprocess.run(
            ["nslookup", "-type=TXT", name],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = f"{completed.stdout}\n{completed.stderr}"
        for line in output.splitlines():
            marker = "text ="
            if marker in line:
                value = line.split(marker, 1)[1].strip().strip('\"')
                if value:
                    records.add(value)
    except Exception:  # noqa: BLE001
        pass
    return records


def _parse_csr(csr_b64: str) -> x509.CertificateSigningRequest:
    """Decode and parse base64url DER CSR payload."""
    try:
        csr_der = _decode_b64url(csr_b64)
        return x509.load_der_x509_csr(csr_der)
    except Exception as exc:  # noqa: BLE001
        raise AcmeProblemError("badCSR", "invalid CSR") from exc


def _csr_dns_names(csr: x509.CertificateSigningRequest) -> set[str]:
    """Extract normalized DNS names from CSR SAN and CN fields."""
    names: set[str] = set()

    try:
        san = csr.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        for dns in san.get_values_for_type(x509.DNSName):
            names.add(normalize_dns_name(dns))
    except x509.ExtensionNotFound:
        pass

    for attr in csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME):
        names.add(normalize_dns_name(attr.value))

    if not names:
        raise AcmeProblemError("badCSR", "CSR must include DNS names")
    return names
