# acmed Overview

> [!TIP]
> **TL;DR**
> `acmed` is a small, policy-driven ACME daemon built on top of a broker-style core, a SQLite-backed worker loop, and a secondary, optional broker API.

Use this document as the source of truth for project purpose, core constraints, and MVP intent.

Owns: project purpose, MVP boundaries, core constraints, and success criteria.

## 1. Purpose

The project goal is to build a central ACME service for internal infrastructure. The service should present a normal ACME directory and protocol surface to clients, evaluate whether the requester is allowed to obtain the requested names, perform the required validation flow, delegate issuance to pluggable backends, and store the resulting artifacts and audit trail.

The project is ACME-first at the product boundary. Internally, it should still use a broker-style core so policy, storage, worker behavior, and issuer integration are not tightly coupled to ACME wire details.

## 2. Core Constraints

1. Make ACME the primary external interface.
2. Keep the broker core protocol-agnostic internally.
3. Model requests as explicit orders with a strict lifecycle.
4. Process authorization, challenge handling, and issuance asynchronously.
5. Keep authorizers, challenge providers, and issuers as separate boundaries.
6. Use YAML for configuration, SQLite for runtime state, and the filesystem for artifacts.
7. Build security in from the start: TLS by default, deny-by-default authorization, least-privilege execution, and redacted audit logging.
8. Keep the MVP lean: one service, one database, one worker loop, and minimal abstraction.
9. Treat the broker API as a secondary interface that must not distort the ACME-visible contract.
10. Require fully documented code: banners, type hints, and meaningful docstrings.

## 3. What The MVP Must Deliver

- asynchronous order processing
- persistent runtime state
- pluggable authorizers, challenge providers, and issuers
- structured audit logging
- ACME protocol support for the documented feature set
- automated testing with `pytest`
- local ACME integration testing with Pebble
- real-client ACME smoke tests with `certbot` and `acme.sh`
- broker REST API only when needed as a secondary integration surface

## 4. Fast Mental Model

- The ACME protocol is the primary interface.
- The worker loop drives the order lifecycle.
- The broker core exists to keep policy, storage, and issuance logic clean behind the ACME surface.
- The broker API is secondary and optional.
- Internal authorization policy is not the same thing as ACME challenge validation.
- Broker-native challenge handling and ACME challenge handling are different workflows.
- The ACME implementation must follow the explicit contract in [`acme-api-reference.md`](./acme-api-reference.md).

## 5. Success Statement

`acmed` is successful when a maintainer can implement a small, secure ACME daemon that behaves like a real ACME server for the documented feature set, passes smoke tests with both `certbot` and `acme.sh`, and uses a small broker-style core to apply policy correctly, process work asynchronously, issue through pluggable backends, and store durable artifacts and audit records.
