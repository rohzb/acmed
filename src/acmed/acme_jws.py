"""ACME JWS parsing and signature verification helpers.

This module contains implementation used by the acmed runtime and plugin surfaces.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from .errors import AcmeProblemError


@dataclass(slots=True)
class VerifiedJws:
    """Normalized verified ACME JWS envelope fields."""
    url: str
    nonce: str
    kid: str | None
    jwk: dict[str, Any] | None
    payload_obj: dict[str, Any]
    payload_raw: bytes
    jwk_thumbprint: str | None


def parse_and_verify_acme_jws(
    body: bytes,
    key_resolver: Callable[[str], dict[str, Any] | None],
    expected_url: str,
) -> VerifiedJws:
    """Parse and verify an ACME JWS request.

    Args:
        body: Raw HTTP request body containing ACME JWS JSON.
        key_resolver: Callback resolving account JWK by `kid` URL.
        expected_url: Absolute target URL expected in protected header.

    Returns:
        VerifiedJws: Verified and normalized request envelope.

    Raises:
        AcmeProblemError: If parsing or signature verification fails.
    """
    try:
        envelope = json.loads(body.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise AcmeProblemError("malformed", "invalid JWS JSON") from exc

    if not isinstance(envelope, dict):
        raise AcmeProblemError("malformed", "JWS body must be an object")

    protected_b64 = _require_str(envelope, "protected")
    payload_b64 = envelope.get("payload")
    if not isinstance(payload_b64, str):
        raise AcmeProblemError("malformed", "payload must be a string")
    signature_b64 = _require_str(envelope, "signature")

    try:
        protected_raw = _b64url_decode(protected_b64)
    except Exception as exc:  # noqa: BLE001
        raise AcmeProblemError("malformed", "protected must be valid base64url") from exc
    try:
        protected = json.loads(protected_raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise AcmeProblemError("malformed", "invalid protected header") from exc

    if not isinstance(protected, dict):
        raise AcmeProblemError("malformed", "protected header must be an object")

    nonce = _require_str(protected, "nonce")
    url = _require_str(protected, "url")
    if url != expected_url:
        raise AcmeProblemError("malformed", "JWS url does not match target endpoint")

    alg = _require_str(protected, "alg")
    if alg == "none":
        raise AcmeProblemError("badSignatureAlgorithm", "algorithm 'none' is not allowed")

    kid = protected.get("kid")
    jwk = protected.get("jwk")
    if kid and jwk:
        raise AcmeProblemError("malformed", "JWS must not include both kid and jwk")
    if not kid and not jwk:
        raise AcmeProblemError("malformed", "JWS must include kid or jwk")

    try:
        payload_raw = _b64url_decode(payload_b64)
    except Exception as exc:  # noqa: BLE001
        raise AcmeProblemError("malformed", "payload must be valid base64url") from exc
    if payload_raw.strip():
        try:
            payload_obj = json.loads(payload_raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise AcmeProblemError("malformed", "payload must be valid JSON") from exc
        if not isinstance(payload_obj, dict):
            raise AcmeProblemError("malformed", "payload must be a JSON object")
    else:
        payload_obj = {}

    try:
        signature = _b64url_decode(signature_b64)
    except Exception as exc:  # noqa: BLE001
        raise AcmeProblemError("malformed", "signature must be valid base64url") from exc
    signing_input = f"{protected_b64}.{payload_b64}".encode("ascii")

    if jwk is not None:
        _verify_with_jwk(jwk=jwk, alg=alg, signing_input=signing_input, signature=signature)
        thumbprint = jwk_thumbprint(jwk)
        return VerifiedJws(
            url=url,
            nonce=nonce,
            kid=None,
            jwk=jwk,
            payload_obj=payload_obj,
            payload_raw=payload_raw,
            jwk_thumbprint=thumbprint,
        )

    if not isinstance(kid, str) or not kid:
        raise AcmeProblemError("malformed", "kid must be a non-empty string")
    account_jwk = key_resolver(kid)
    if account_jwk is None:
        raise AcmeProblemError("accountDoesNotExist", "unknown ACME account", http_status=403)
    _verify_with_jwk(jwk=account_jwk, alg=alg, signing_input=signing_input, signature=signature)
    return VerifiedJws(
        url=url,
        nonce=nonce,
        kid=kid,
        jwk=None,
        payload_obj=payload_obj,
        payload_raw=payload_raw,
        jwk_thumbprint=None,
    )


def verify_external_account_binding(
    external_account_binding: dict[str, Any],
    expected_url: str,
    account_jwk: dict[str, Any],
    secret_lookup: Callable[[str], str | None],
) -> str:
    """Verify ACME External Account Binding payload and signature.

    Args:
        external_account_binding: Parsed JWS object from `externalAccountBinding`.
        expected_url: Absolute ACME `newAccount` URL expected in the protected header.
        account_jwk: Account public JWK that must match the embedded EAB payload.
        secret_lookup: Callback that resolves an EAB HMAC secret by key id.

    Returns:
        str: Verified EAB key identifier (`kid`).
    """
    if not isinstance(external_account_binding, dict):
        raise AcmeProblemError("malformed", "externalAccountBinding must be an object")

    protected_b64 = _require_str(external_account_binding, "protected")
    payload_b64 = _require_str(external_account_binding, "payload")
    signature_b64 = _require_str(external_account_binding, "signature")

    try:
        protected = json.loads(_b64url_decode(protected_b64).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise AcmeProblemError("malformed", "invalid EAB protected header") from exc
    if _require_str(protected, "alg") != "HS256":
        raise AcmeProblemError("badSignatureAlgorithm", "EAB requires HS256")

    kid = _require_str(protected, "kid")
    if _require_str(protected, "url") != expected_url:
        raise AcmeProblemError("malformed", "EAB url mismatch")

    secret = secret_lookup(kid)
    if secret is None:
        raise AcmeProblemError("unauthorized", "unknown EAB key id", http_status=403)

    expected_payload = _b64url_encode(_json_canonical_bytes(account_jwk))
    if payload_b64 != expected_payload:
        raise AcmeProblemError("malformed", "EAB payload does not match account key")

    signing_input = f"{protected_b64}.{payload_b64}".encode("ascii")
    try:
        provided = _b64url_decode(signature_b64)
    except Exception as exc:  # noqa: BLE001
        raise AcmeProblemError("malformed", "invalid EAB signature encoding") from exc
    computed = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(provided, computed):
        raise AcmeProblemError("unauthorized", "EAB signature verification failed", http_status=403)
    return kid


def jwk_thumbprint(jwk: dict[str, Any]) -> str:
    """Compute an RFC 7638 JWK thumbprint for an EC or RSA key.

    Args:
        jwk: JWK mapping containing the required key-type fields.

    Returns:
        Base64url-encoded SHA-256 thumbprint value.
    """
    kty = jwk.get("kty")
    if kty == "EC":
        canonical = {
            "crv": _require_str(jwk, "crv"),
            "kty": "EC",
            "x": _require_str(jwk, "x"),
            "y": _require_str(jwk, "y"),
        }
    elif kty == "RSA":
        canonical = {
            "e": _require_str(jwk, "e"),
            "kty": "RSA",
            "n": _require_str(jwk, "n"),
        }
    else:
        raise AcmeProblemError("badPublicKey", f"unsupported JWK kty: {kty}")

    digest = hashlib.sha256(_json_canonical_bytes(canonical)).digest()
    return _b64url_encode(digest)


def _verify_with_jwk(jwk: dict[str, Any], alg: str, signing_input: bytes, signature: bytes) -> None:
    """Verify detached JWS signature for the selected algorithm."""
    public_key = _public_key_from_jwk(jwk)

    try:
        if alg == "ES256":
            if not isinstance(public_key, ec.EllipticCurvePublicKey):
                raise AcmeProblemError("badPublicKey", "ES256 requires EC P-256 key")
            if len(signature) != 64:
                raise AcmeProblemError("malformed", "invalid ES256 signature length")
            r = int.from_bytes(signature[:32], "big")
            s = int.from_bytes(signature[32:], "big")
            public_key.verify(encode_dss_signature(r, s), signing_input, ec.ECDSA(hashes.SHA256()))
            return

        if alg == "RS256":
            if not isinstance(public_key, rsa.RSAPublicKey):
                raise AcmeProblemError("badPublicKey", "RS256 requires RSA key")
            public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
            return

        raise AcmeProblemError("badSignatureAlgorithm", f"unsupported alg: {alg}")
    except InvalidSignature as exc:
        raise AcmeProblemError("unauthorized", "JWS signature verification failed", http_status=403) from exc


def _public_key_from_jwk(jwk: dict[str, Any]):
    """Construct cryptography public key instance from JWK fields."""
    kty = jwk.get("kty")
    if kty == "EC":
        crv = _require_str(jwk, "crv")
        if crv != "P-256":
            raise AcmeProblemError("badPublicKey", f"unsupported EC curve: {crv}")
        x = int.from_bytes(_b64url_decode(_require_str(jwk, "x")), "big")
        y = int.from_bytes(_b64url_decode(_require_str(jwk, "y")), "big")
        return ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()

    if kty == "RSA":
        n = int.from_bytes(_b64url_decode(_require_str(jwk, "n")), "big")
        e = int.from_bytes(_b64url_decode(_require_str(jwk, "e")), "big")
        return rsa.RSAPublicNumbers(e, n).public_key()

    raise AcmeProblemError("badPublicKey", f"unsupported key type: {kty}")


def _json_canonical_bytes(value: dict[str, Any]) -> bytes:
    """Serialize mapping with deterministic canonical JSON encoding."""
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _require_str(payload: dict[str, Any], key: str) -> str:
    """Require non-empty string field in parsed JSON object."""
    value = payload.get(key)
    if not isinstance(value, str) or value == "":
        raise AcmeProblemError("malformed", f"{key} must be a non-empty string")
    return value


def _b64url_decode(value: str) -> bytes:
    """Decode base64url value with optional missing padding."""
    padding_needed = (-len(value)) % 4
    return base64.urlsafe_b64decode((value + ("=" * padding_needed)).encode("ascii"))


def _b64url_encode(value: bytes) -> str:
    """Encode bytes as unpadded base64url string."""
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
