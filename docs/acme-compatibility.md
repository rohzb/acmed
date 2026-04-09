# acmed ACME Compatibility Notes

> [!TIP]
> **TL;DR**
> This document collects practical compatibility notes and smoke-test examples for `certbot` and `acme.sh`. The protocol contract itself lives in [`acme-api-reference.md`](./acme-api-reference.md).

Use this file for practical client validation notes, not as the normative ACME contract. For client-visible protocol rules, use [`acme-api-reference.md`](./acme-api-reference.md).

Owns: client smoke-test notes, interoperability reminders, and practical compatibility validation guidance.

## 1. Purpose

Use this document for:

- client-oriented smoke-test examples
- compatibility validation notes
- practical reminders about how `certbot` and `acme.sh` should interact with the ACME interface

Do not use this document as the main protocol reference. It exists to validate and exercise the contract defined in [`acme-api-reference.md`](./acme-api-reference.md).

## 2. Compatibility Rules

- point clients at the ACME directory URL
- advertise only the ACME features actually implemented
- do not claim compatibility with a named client unless that client has been tested
- keep the documented supported feature set synchronized with the real implementation
- for the MVP, support both `http-01` and `dns-01`
- for the MVP, require ACME External Account Binding for account creation and test clients with that enrollment flow

When this document and [`acme-api-reference.md`](./acme-api-reference.md) differ, treat the API reference as authoritative and use this file only for practical validation guidance.

Preferred testing environments:

- use Pebble as the default local ACME test server for automated integration and smoke tests
- use Let’s Encrypt staging only as optional external verification

Pebble setup assumption:

- the local ACME test environment should expose a normal ACME directory URL shape so `certbot` and `acme.sh` can be pointed at it the same way they would be pointed at a real ACME server

## 3. Client Smoke-Test Examples

These examples are illustrative smoke-test targets, not production runbooks.

They intentionally omit exact External Account Binding command-line flags because client support and flag names can vary by tool and version. The smoke-test workflow must still exercise EAB even when the short examples below do not show the full enrollment command, and the examples are sketches rather than canonical commands for every supported client version.

### certbot example

```bash
certbot certonly \
  --server https://<host>/acme/directory \
  --manual \
  --preferred-challenges dns \
  -d example.org
```

The real smoke test should also cover an `http-01` path, for example with a manual or test harness flow that provisions the token response material expected by the server.

### acme.sh example

```bash
acme.sh --issue \
  --server https://<host>/acme/directory \
  --dns \
  -d example.org
```

The real smoke test suite should include one `dns-01` issuance and one `http-01` issuance rather than treating one of the two challenge types as optional.

The exact smoke-test command may vary by challenge method, but the implementation should support the normal directory-URL based client model.

## 4. What To Validate

For both `certbot` and `acme.sh`, validate at least:

- directory discovery
- nonce handling
- account creation with External Account Binding
- order creation
- challenge acknowledgement
- finalize flow
- certificate download

Also validate:

- across the named-client smoke-test set, both `http-01` and `dns-01` challenge paths
- failures are reported in ACME-compatible ways
- unsupported features are not advertised
- wildcard behavior matches the documented supported challenge set

## 5. Staging Verification Notes

Let’s Encrypt staging can be useful for additional confidence because it behaves like a real external ACME environment, but it should not be the default automated dependency.

Use staging when:

- preparing for release
- confirming behavior beyond the local Pebble environment
- manually checking interoperability in a more realistic network setting

Do not make normal automated test runs depend on staging availability.

## 6. References

- [`acme-api-reference.md`](./acme-api-reference.md)
- RFC 8555: https://datatracker.ietf.org/doc/html/rfc8555
- Certbot usage docs: https://eff-certbot.readthedocs.io/en/latest/using.html
- acme.sh server parameter notes: https://github-wiki-see.page/m/acmesh-official/acme.sh/wiki/Server
- Let’s Encrypt staging environment: https://letsencrypt.org/docs/staging-environment/
- Pebble: https://github.com/letsencrypt/pebble
