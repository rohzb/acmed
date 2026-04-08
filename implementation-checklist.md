# acmed Implementation Checklist

> [!TIP]
> **TL;DR**
> This is the shortest implementation-oriented checklist for building the `acmed` MVP from the design documents in this folder.

Use [`incremental-delivery.md`](/workspaces/cfg-pi-wizzy/local/acmed/incremental-delivery.md) to decide what to build first and what to delay to later iterations.

## 1. Core Domain

- [ ] Define typed config models.
- [ ] Define order models and state values.
- [ ] Implement the order lifecycle state machine.
- [ ] Define interfaces for authorizers, challenge providers, and issuers.
- [ ] Add core error types.

## 2. Persistence

- [ ] Create SQLite schema for `orders`, `issuance_attempts`, and `audit_events`.
- [ ] Implement runtime-state storage helpers.
- [ ] Implement artifact layout and sensitive-file permissions.
- [ ] Implement audit-event writes.
- [ ] Implement deduplication key handling.

## 3. Broker Flow

- [ ] Normalize broker-native requests.
- [ ] Resolve policy and issuer/challenge choices.
- [ ] Persist new orders as `pending`.
- [ ] Implement asynchronous worker pickup.
- [ ] Transition orders through authorization, issuance, and terminal states.

## 4. Broker API

- [ ] Add `POST /api/v1/orders`.
- [ ] Add `GET /api/v1/orders/<order_id>`.
- [ ] Add `GET /api/v1/orders`.
- [ ] Enforce requester authentication and order access control.

## 5. Security Baseline

- [ ] Enforce TLS outside explicit local development mode.
- [ ] Enforce deny-by-default authorization.
- [ ] Redact secrets from logs and audit records.
- [ ] Use hardened subprocess wrappers.
- [ ] Add rate limiting and bounded retries.

## 6. Broker-Native Plugins

- [ ] Implement at least one authorizer.
- [ ] Implement at least one broker-native challenge path.
- [ ] Implement a mock issuer.
- [ ] Implement a command-based issuer skeleton.

## 7. ACME Adapter

- [ ] Implement the ACME resources defined in [`acme-api-reference.md`](/workspaces/cfg-pi-wizzy/local/acmed/acme-api-reference.md).
- [ ] Keep ACME behavior protocol-correct and broker-internal behavior separate.
- [ ] Enforce identifier support rules, ownership checks, and DNS normalization.
- [ ] Advertise only the ACME features actually implemented.

## 8. Tests

- [ ] State machine tests.
- [ ] Config validation tests.
- [ ] Broker API tests.
- [ ] Worker happy-path and denial-path tests.
- [ ] Artifact and audit tests.
- [ ] `pytest` is configured as the canonical Python test runner.
- [ ] ACME integration tests run against Pebble.
- [ ] ACME protocol tests for the documented supported feature set.
- [ ] Real-client smoke test with `certbot`.
- [ ] Real-client smoke test with `acme.sh`.
- [ ] Optional Let’s Encrypt staging verification is documented separately from the default test flow.

## 9. Documentation

- [ ] Keep banners, type hints, and docstrings in generated code.
- [ ] Provide a top-level README.
- [ ] Provide example configuration.
- [ ] Keep ACME-visible behavior documented in [`acme-api-reference.md`](/workspaces/cfg-pi-wizzy/local/acmed/acme-api-reference.md).

## 10. MVP Done

- [ ] Broker-native ordering works end to end.
- [ ] Worker processing is asynchronous and durable.
- [ ] Security defaults are enforced.
- [ ] ACME behavior matches the documented supported feature set.
- [ ] `certbot` and `acme.sh` smoke tests pass.

## 11. Authoritative References

- [ ] Architecture decisions stay aligned with [`architecture.md`](/workspaces/cfg-pi-wizzy/local/acmed/architecture.md).
- [ ] Order lifecycle, schema, storage, and config stay aligned with [`data-model.md`](/workspaces/cfg-pi-wizzy/local/acmed/data-model.md).
- [ ] Security and runtime behavior stay aligned with [`security-operations.md`](/workspaces/cfg-pi-wizzy/local/acmed/security-operations.md).
- [ ] Delivery sequencing stays aligned with [`incremental-delivery.md`](/workspaces/cfg-pi-wizzy/local/acmed/incremental-delivery.md).
- [ ] ACME-visible behavior stays aligned with [`acme-api-reference.md`](/workspaces/cfg-pi-wizzy/local/acmed/acme-api-reference.md).
