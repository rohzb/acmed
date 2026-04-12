# acmed Implementation Status

This document summarizes what is currently implemented in this repository state.

## 1. Overview

`acmed` currently includes a modular Python implementation under `src/acmed` with:

- ACME-first HTTP handlers
- RFC-style ACME JOSE request verification (`jwk` and `kid` request signing)
- YAML-based configuration loading and validation
- SQLite-backed runtime state and ACME persistence tables
- asynchronous worker processing with order claim/recovery behavior
- plugin boundaries for authorizers, proof handlers, and issuer backends
- `allow_all` and `source_subnet` authorizer implementations
- mock issuer and subprocess wrappers for `acme.sh` and `certbot`
- challenge validation for `http-01`, `dns-01`, and `tls-alpn-01`
- pre-authorization enforcement at ACME `newOrder` using configured authorizers and request source evidence
- policy-scoped `challenge_validation_mode` with `strict` default and development-only `trusted_bypass`

## 2. Implemented Module Layout

- `main.py`: runtime wiring and WSGI entrypoint
- `acme_api.py`: ACME resource handlers and ACME-to-core mapping
- `acme_jws.py`: ACME JWS parsing, signature verification, JWK thumbprints, EAB checks
- `api.py`: health and admin endpoints
- `auth.py`: token auth and admin subject enforcement
- `config.py`: YAML config models and fail-closed validation
- `models.py`: domain entities, enums, and dedupe helpers
- `policy.py`: matcher compilation and policy resolution
- `storage.py`: SQLite schema and repositories, artifact writer, nonce handling
- `worker.py`: claim loop, authorization/proof/issuance flow, retries, expiration
- `audit.py`: redaction and structured audit event creation
- `authorizers/`, `proofs/`, `issuers/`: pluggable backend interfaces and implementations

## 3. Runtime Artifacts

Default local examples use:

- SQLite database: `data/acmed.db`
- artifact root: `data/orders/`

Per-order artifacts include files such as:

- `private.key`
- `certificate.pem`
- `chain.pem`
- `fullchain.pem`
- `issuer-output.log`
- `challenge-output.log`

## 4. Test Status

Current tests are in `tests/` and run with:

```bash
PYTHONPATH=src pytest
```

The suite currently covers:

- config fail-closed behavior for required secret env vars
- policy exact/suffix matcher behavior
- deduplication behavior for active orders
- order-claim/finalize gating behavior for ACME-driven orders
- sensitive artifact file permissions
- ACME JWS verification paths (`jwk` and `kid`)
- ACME `newOrder` pre-authorization enforcement
- DNS challenge validation success and mismatch paths

## 5. Container Examples

Example container assets are provided in [`../docker/README.md`](../../docker/README.md):

- `docker/Dockerfile`
- `docker/docker-compose.yml`
- `docker/.env.example`
- `docker/config/config.active.example.yml`
- `docker/config/config.yml` (local active config copied from one of the profiles)
- `docker/config/config.allow-all.yml`
- `docker/config/config.source-subnet-local.yml`
- `docker/config/config.trusted-bypass-local.yml`

## 6. Known Minimal Gaps

For the minimal additions needed to fully align runtime behavior with the full documentation set, see:

- [`implementation-gaps.md`](./implementation-gaps.md)
