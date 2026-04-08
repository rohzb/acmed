# acmed Implementation Checklist

> [!TIP]
> **TL;DR**
> This is the shortest implementation-oriented checklist for building the `acmed` MVP from the design documents in this folder.

Use [`delivery-plan.md`](./delivery-plan.md) to decide what to build first and what to delay to later iterations.

Use [`policy-config.md`](./policy-config.md) for matcher syntax and configuration details, and use [`broker-api-reference.md`](./broker-api-reference.md) for broker HTTP contract details.

This file is intentionally terse. Use the other documents for the underlying system rules and contracts.

## 1. Iteration 0: Bootstrapping

- [ ] Define typed config models.
- [ ] Define typed config models for token subjects, admin subjects, request limits, order TTL, claim TTL, and retry bounds.
- [ ] Define order models and state values.
- [ ] Implement the order lifecycle state machine.
- [ ] Define interfaces for authorizers, challenge providers, and issuers.
- [ ] Add core error types.
- [ ] Start the project locally with basic app startup.
- [ ] Run a basic `pytest` pass successfully.

## 2. Iteration 1: Broker-Native Happy Path

- [ ] Create SQLite schema for `orders`, `issuance_attempts`, and `audit_events`.
- [ ] Implement runtime-state storage helpers.
- [ ] Implement artifact layout and sensitive-file permissions.
- [ ] Implement audit-event writes.
- [ ] Implement deduplication key handling.
- [ ] Normalize broker-native requests.
- [ ] Enforce request size and SAN-count limits at the HTTP boundary.
- [ ] Parse and validate `allowed_domains` entries with explicit `syntax` and `value` fields.
- [ ] Support `exact` and `suffix` policy syntax in the broker-first matcher.
- [ ] Resolve policy and issuer/challenge choices.
- [ ] Enforce CSR mode selection from `csr_pem` presence versus selected policy mode.
- [ ] Persist new orders as `pending`.
- [ ] Implement asynchronous worker pickup.
- [ ] Restrict worker claim pickup to `pending` and recoverable `authorized` orders.
- [ ] Transition orders through authorization, issuance, and terminal states.

- [ ] Add `POST /api/v1/orders`.
- [ ] Add `GET /api/v1/orders/<order_id>`.
- [ ] Add `GET /api/v1/orders`.
- [ ] Keep broker and admin order-list responses minimal and newest-first by default.
- [ ] Return `404` for requester-scoped reads of both missing and not-owned orders.
- [ ] Enforce requester authentication and order access control.
- [ ] Enforce admin access through the explicit admin-subject allow-list.

- [ ] Enforce TLS outside explicit local development mode.
- [ ] Enforce deny-by-default authorization.
- [ ] Redact secrets from logs and audit records.

- [ ] Implement at least one authorizer.
- [ ] Implement a mock issuer.
- [ ] `pytest` is configured as the canonical Python test runner.
- [ ] State machine tests, config validation tests, broker API tests, policy-matching tests, and happy-path worker tests pass.

## 3. Iteration 2: Failure And Denial Paths

- [ ] Add denial-path handling.
- [ ] Add failure-path handling.
- [ ] Add retry classification and bounded retry behavior.
- [ ] Reject unsupported or malformed policy matcher entries fail-closed.
- [ ] Add secret-redaction checks.
- [ ] Add worker denial-path and failure-path tests.

## 4. Iteration 3: Broker-Native Challenge Expansion

- [ ] Implement the explicit `no-challenge` path.
- [ ] Implement at least one broker-native challenge-provider path if needed.
- [ ] Keep broker-native challenge logic separate from future ACME challenge behavior.

## 5. Iteration 4: Command-Based Issuer Integration

- [ ] Use hardened subprocess wrappers.
- [ ] Implement a command-based issuer skeleton.
- [ ] Add subprocess timeout, logging, and sanitized environment handling tests.

## 6. Iteration 5: ACME Minimal Compatible Flow

- [ ] Implement the ACME resources defined in [`acme-api-reference.md`](./acme-api-reference.md).
- [ ] Keep ACME behavior protocol-correct and broker-internal behavior separate.
- [ ] Enforce identifier support rules, ownership checks, and DNS normalization.
- [ ] Require External Account Binding for ACME account creation.
- [ ] Implement both `http-01` and `dns-01` challenge flows.
- [ ] Advertise only the ACME features actually implemented.
- [ ] ACME integration tests run against Pebble.
- [ ] ACME protocol tests for the documented supported feature set.

## 7. Iteration 6: Compatibility Hardening

- [ ] Real-client smoke test with `certbot`.
- [ ] Real-client smoke test with `acme.sh`.
- [ ] Optional Let’s Encrypt staging verification is documented separately from the default test flow.

## 8. Documentation

- [ ] Keep banners, type hints, and docstrings in generated code.
- [ ] Provide a top-level README.
- [ ] Provide example configuration.
- [ ] Keep broker-native request and response behavior documented in [`broker-api-reference.md`](./broker-api-reference.md).
- [ ] Keep policy and configuration behavior documented in [`policy-config.md`](./policy-config.md).
- [ ] Keep ACME-visible behavior documented in [`acme-api-reference.md`](./acme-api-reference.md).
- [ ] Keep broker implementation defaults synchronized across [`README.md`](../README.md), [`policy-config.md`](./policy-config.md), and [`implementation-guide.md`](./implementation-guide.md).

## 9. MVP Done

- [ ] Broker-native ordering works end to end.
- [ ] Worker processing is asynchronous and durable.
- [ ] Security defaults are enforced.
- [ ] ACME behavior matches the documented supported feature set.
- [ ] `certbot` and `acme.sh` smoke tests pass.
