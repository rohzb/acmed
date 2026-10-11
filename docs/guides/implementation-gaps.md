---
title: Implementation Gaps And Minimal Additions
nav_title: Implementation gaps
---

# Implementation Gaps And Minimal Additions

This note tracks the small remaining gaps to bring runtime behavior in line with the ACME and security docs.

## Client certificate reuse limits

Public-artifact reuse is opt-in for `acme_sh`; it does not cover `certbot` or
service-generated-key requests. It cannot recover a client's lost private key.
No private-key escrow/recovery API, upstream revocation discovery, historical
certificate import or per-key serialization of concurrent upstream requests is
implemented. Remove cache entries following external revocation and use normal
client state preservation for VM rebuilds. A new cache is populated only by
successful issuance after enabling it; it cannot resolve an already exhausted
quota for a new client key.

## Gap 1: ACME challenge robustness and test coverage

Current state:
- `http-01`, `dns-01`, and `tls-alpn-01` validation paths are implemented.
- Unit coverage exists for `dns-01` validation behavior.
- Deterministic integration coverage for live DNS and TLS challenge environments is not yet included in the automated test suite.

Minimal required addition:
- Add integration tests for `dns-01` and `tls-alpn-01` against deterministic local fixtures/environments.
