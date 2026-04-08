# acmed Project Brief

> [!TIP]
> **TL;DR**
> `acmed` is a small, policy-driven certificate broker with a broker-native API, a SQLite-backed worker loop, and an optional ACME-compatible adapter.

## 1. Purpose

This folder contains the design set for a new Python project named `acmed`.

The project goal is to build a central certificate brokerage service for internal infrastructure. The service accepts certificate requests, evaluates whether the requester is allowed to obtain the requested names, optionally performs challenge validation, delegates issuance to pluggable backends, and stores the resulting artifacts and audit trail.

`acmed` is not ACME-first. ACME support is an adapter layer, not the core domain model.

## 2. Core Constraints

1. Keep the broker core protocol-agnostic.
2. Model requests as explicit orders with a strict lifecycle.
3. Process authorization, challenge handling, and issuance asynchronously.
4. Keep authorizers, challenge providers, and issuers as separate boundaries.
5. Use YAML for configuration, SQLite for runtime state, and the filesystem for artifacts.
6. Build security in from the start: TLS by default, deny-by-default authorization, least-privilege execution, and redacted audit logging.
7. Keep the MVP lean: one service, one database, one worker loop, and minimal abstraction.
8. Require fully documented code: banners, type hints, and meaningful docstrings.

## 3. What The MVP Must Deliver

- broker REST API
- asynchronous order processing
- persistent runtime state
- pluggable authorizers, challenge providers, and issuers
- structured audit logging
- ACME adapter for the documented supported feature set
- automated testing with `pytest`
- local ACME integration testing with Pebble
- real-client ACME smoke tests with `certbot` and `acme.sh`

## 4. Reading Order

1. [`description.md`](./description.md)
2. [`architecture.md`](./architecture.md)
3. [`data-model.md`](./data-model.md)
4. [`security-operations.md`](./security-operations.md)
5. [`incremental-delivery.md`](./incremental-delivery.md)
6. [`implementation-checklist.md`](./implementation-checklist.md)
7. [`implementation-guide.md`](./implementation-guide.md)
8. [`acme-api-reference.md`](./acme-api-reference.md)
9. [`acme-compatibility.md`](./acme-compatibility.md)

## 5. Fast Mental Model

- The broker API is the primary interface.
- The worker loop drives the order lifecycle.
- Internal authorization policy is not the same thing as ACME challenge validation.
- Broker-native challenge handling and ACME challenge handling are different workflows.
- The ACME adapter must follow the explicit contract in [`acme-api-reference.md`](./acme-api-reference.md).

## 6. Success Statement

`acmed` is successful when a maintainer can implement a small, secure broker core that accepts normalized certificate requests, applies internal policy correctly, processes them asynchronously, issues through pluggable backends, stores durable artifacts and audit records, and exposes ACME behavior that matches the documented contract closely enough to pass smoke tests with both `certbot` and `acme.sh`.
