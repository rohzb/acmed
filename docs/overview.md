# acmed Overview

> [!TIP]
> **TL;DR**
> `acmed` is a small policy-driven ACME service with a thin certificate-brokering core that accepts ACME requests, applies local authorization and proof rules, and delegates real issuance to external issuer adapters such as `acme.sh` and `certbot`.

Use this document as the source of truth for project purpose, core constraints, and MVP intent.

Owns: project purpose, MVP boundaries, core constraints, and success criteria.

## 1. Purpose

The project goal is to build a central ACME service for internal infrastructure.

`acmed` should sit between:

- internal clients that need certificates
- external issuer tooling and certificate authorities that can satisfy the real public-validation flow

The service should:

- authenticate the internal requester
- decide whether that requester may ask for the requested names
- optionally require an internal proof or approval step before continuing
- choose an allowed issuer profile
- delegate actual issuance to an external issuer adapter
- store resulting artifacts and an audit trail

The core design intent is to keep `acmed` relatively thin. It is not supposed to become a full certificate authority or a large challenge-execution platform of its own. Its job is brokering, policy enforcement, orchestration, and auditability.

## 2. Core Constraints

1. Make ACME the primary product interface.
2. Keep requester authorization separate from public CA challenge fulfillment.
3. Treat external issuer integrations as the place where real ACME or CA-specific challenge plugins run.
4. Keep broad external issuer credentials centralized and unavailable to ordinary requesters.
5. Model requests as explicit orders with a strict lifecycle.
6. Process authorization, optional internal proof, and issuance asynchronously.
7. Keep authorizers, proof handlers, and issuers as separate boundaries.
8. Use YAML for configuration, SQLite for runtime state, and the filesystem for artifacts.
9. Build security in from the start: TLS by default, deny-by-default authorization, least-privilege execution, and redacted audit logging.
10. Keep the MVP lean: one service, one database, one worker loop, and minimal abstraction.
11. Keep the broker-native API, if added later, secondary and out of scope for the first implementation.
12. Require fully documented code: banners, type hints, and meaningful docstrings.

## 3. What The MVP Must Deliver

- asynchronous order processing
- persistent runtime state
- pluggable authorizers
- pluggable internal proof handlers
- pluggable issuers, including at least one real issuer path
- structured audit logging
- automated testing with `pytest`
- local integration testing against a deterministic ACME-compatible external test CA such as Pebble
- ACME protocol support for the documented feature set
- broker-native API only if added in a later expansion

## 4. Fast Mental Model

- Internal clients use the ACME API exposed by `acmed`.
- `acmed` decides whether the requester is allowed to ask for that name.
- `acmed` may require an internal proof or approval step before using a privileged issuer.
- `acmed` then invokes an external issuer adapter.
- The issuer adapter owns the broad validation credentials and challenge plugins needed to talk to the real external CA.
- Internal requester permissions are narrower than external issuer capabilities.
- Policy is the boundary that prevents a broad external issuer from being usable for every client.

## 5. Success Statement

`acmed` is successful when a maintainer can implement a small, secure ACME service that behaves honestly for the documented feature set, applies policy correctly, invokes external issuer tooling such as `acme.sh` or `certbot` safely, keeps high-privilege challenge credentials centralized, and stores durable artifacts and audit records without exposing those broader capabilities to ordinary requesters.
