import base64
import json

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

import pytest

from acmed.acme_jws import jwk_thumbprint, parse_and_verify_acme_jws, verify_external_account_binding
from acmed.errors import AcmeProblemError


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _make_ec_jwk(private_key: ec.EllipticCurvePrivateKey) -> dict[str, str]:
    nums = private_key.public_key().public_numbers()
    return {
        "kty": "EC",
        "crv": "P-256",
        "x": _b64url(nums.x.to_bytes(32, "big")),
        "y": _b64url(nums.y.to_bytes(32, "big")),
    }


def _sign_es256(private_key: ec.EllipticCurvePrivateKey, signing_input: bytes) -> bytes:
    der = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def test_parse_and_verify_with_jwk_header():
    key = ec.generate_private_key(ec.SECP256R1())
    jwk = _make_ec_jwk(key)

    protected = {
        "alg": "ES256",
        "nonce": "nonce-1",
        "url": "https://acme.example.org/acme/new-account",
        "jwk": jwk,
    }
    payload = {"contact": ["mailto:test@example.org"]}

    protected_b64 = _b64url(json.dumps(protected, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{protected_b64}.{payload_b64}".encode("ascii")
    sig_b64 = _b64url(_sign_es256(key, signing_input))

    body = json.dumps({"protected": protected_b64, "payload": payload_b64, "signature": sig_b64}).encode("utf-8")
    verified = parse_and_verify_acme_jws(
        body=body,
        key_resolver=lambda kid: None,
        expected_url="https://acme.example.org/acme/new-account",
    )

    assert verified.kid is None
    assert verified.jwk == jwk
    assert verified.jwk_thumbprint == jwk_thumbprint(jwk)
    assert verified.payload_obj["contact"] == ["mailto:test@example.org"]


def test_parse_and_verify_with_kid_header_uses_resolver():
    key = ec.generate_private_key(ec.SECP256R1())
    jwk = _make_ec_jwk(key)

    protected = {
        "alg": "ES256",
        "nonce": "nonce-2",
        "url": "https://acme.example.org/acme/new-order",
        "kid": "https://acme.example.org/acme/account/acc-1",
    }
    payload = {"identifiers": [{"type": "dns", "value": "host1.lab.example.org"}]}

    protected_b64 = _b64url(json.dumps(protected, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{protected_b64}.{payload_b64}".encode("ascii")
    sig_b64 = _b64url(_sign_es256(key, signing_input))

    body = json.dumps({"protected": protected_b64, "payload": payload_b64, "signature": sig_b64}).encode("utf-8")
    verified = parse_and_verify_acme_jws(
        body=body,
        key_resolver=lambda kid: jwk if kid.endswith("/acc-1") else None,
        expected_url="https://acme.example.org/acme/new-order",
    )

    assert verified.kid == "https://acme.example.org/acme/account/acc-1"
    assert verified.jwk is None
    assert verified.payload_obj["identifiers"][0]["value"] == "host1.lab.example.org"


def test_parse_and_verify_accepts_empty_payload_for_post_as_get():
    key = ec.generate_private_key(ec.SECP256R1())
    jwk = _make_ec_jwk(key)

    protected = {
        "alg": "ES256",
        "nonce": "nonce-3",
        "url": "https://acme.example.org/acme/order/order-1",
        "kid": "https://acme.example.org/acme/account/acc-1",
    }

    protected_b64 = _b64url(json.dumps(protected, separators=(",", ":")).encode("utf-8"))
    payload_b64 = ""
    signing_input = f"{protected_b64}.{payload_b64}".encode("ascii")
    sig_b64 = _b64url(_sign_es256(key, signing_input))

    body = json.dumps({"protected": protected_b64, "payload": payload_b64, "signature": sig_b64}).encode("utf-8")
    verified = parse_and_verify_acme_jws(
        body=body,
        key_resolver=lambda kid: jwk if kid.endswith("/acc-1") else None,
        expected_url="https://acme.example.org/acme/order/order-1",
    )

    assert verified.kid == "https://acme.example.org/acme/account/acc-1"
    assert verified.payload_raw == b""
    assert verified.payload_obj == {}


def test_parse_and_verify_rejects_invalid_protected_base64url():
    body = json.dumps({"protected": "%%%not-b64%%%", "payload": "", "signature": "AA"}).encode("utf-8")
    with pytest.raises(AcmeProblemError) as exc:
        parse_and_verify_acme_jws(
            body=body,
            key_resolver=lambda kid: None,
            expected_url="https://acme.example.org/acme/new-order",
        )
    assert exc.value.code == "malformed"


def test_verify_external_account_binding_rejects_invalid_protected_header():
    with pytest.raises(AcmeProblemError) as exc:
        verify_external_account_binding(
            external_account_binding={
                "protected": "%%%bad%%%",
                "payload": "",
                "signature": "",
            },
            expected_url="https://acme.example.org/acme/new-account",
            account_jwk={"kty": "EC", "crv": "P-256", "x": "AA", "y": "BB"},
            secret_lookup=lambda kid: "secret",
        )
    assert exc.value.code == "malformed"
