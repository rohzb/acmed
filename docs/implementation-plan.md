# acmed Implementation Plan

> [!TIP]
> **TL;DR**
> Use this file for delivery order, implementation checklists, and MVP done criteria. Use the topic docs for the actual system contract.

Owns: implementation sequencing, iteration scope, execution checklists, stop rules, and MVP completion criteria.

## 1. Purpose

Build `acmed` as a sequence of small, working, testable slices.

Use this document for:

- what to build first
- what each iteration must include
- what to delay
- the shortest actionable checklist for each iteration
- when to stop and reassess

Use companion docs for topic-specific rules:

- [`architecture.md`](./architecture.md): runtime shape and boundaries
- [`data-model.md`](./data-model.md): lifecycle, persistence, and artifacts
- [`policy-config.md`](./policy-config.md): config schema, identity, policy matching, and defaults
- [`broker-api-reference.md`](./broker-api-reference.md): broker-native HTTP contract
- [`security-operations.md`](./security-operations.md): security and runtime posture
- [`acme-api-reference.md`](./acme-api-reference.md): ACME-visible behavior

## 2. Core Delivery Rule

Do not build for the final shape first.

Build the smallest correct slice, prove it works, then expand it.

## 3. Delivery Rules

Each iteration should:

1. Deliver working behavior, not scaffolding-only structure.
2. Add only the abstractions needed by the current iteration.
3. Keep tests green before moving to the next iteration.
4. Keep docs truthful about what is and is not supported.
5. Avoid advertising unsupported ACME features or challenge types.
6. Prefer simple code over speculative “future-proof” structure.
7. Keep security defaults on from the first iteration that exposes real behavior.

Testing baseline for every iteration:

- Python tests run under `pytest`
- local integration tests prefer deterministic local dependencies
- ACME integration uses Pebble by default rather than external network dependencies

## 4. Iteration 0: Bootstrapping

Goal:

- establish project layout, core models, config loading, and basic local execution

Include:

- package skeleton
- typed config models for token subjects, admin subjects, request limits, order TTL, claim TTL, and retry bounds
- order models and state values
- order lifecycle state machine
- interfaces for authorizers, challenge providers, and issuers
- core error types
- basic app startup

Do not include yet:

- real issuer execution
- ACME endpoints
- broad plugin ecosystems

Checklist:

- [ ] Define typed config models.
- [ ] Define order models and state values.
- [ ] Implement the order lifecycle state machine.
- [ ] Define interfaces for authorizers, challenge providers, and issuers.
- [ ] Add core error types.
- [ ] Start the project locally with basic app startup.
- [ ] Run a basic `pytest` pass successfully.

Done when:

- the project starts locally
- config validation works
- basic tests run successfully

## 5. Iteration 1: Broker-Native Happy Path

Goal:

- implement one complete broker-native issuance flow

Include:

- broker API order creation
- SQLite order persistence
- worker pickup of `pending` orders
- one authorizer path
- one issuer path using the mock issuer
- artifact write path

Do not include yet:

- command-based external issuer behavior
- ACME compatibility
- multiple challenge modes unless one is needed for the slice

Checklist:

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
- [ ] Configure `pytest` as the canonical Python test runner.
- [ ] Pass state-machine, config-validation, broker-API, policy-matching, and happy-path worker tests.

Done when:

- a broker-native request can reach `issued`
- artifacts and audit records are written
- happy-path tests pass

## 6. Iteration 2: Failure And Denial Paths

Goal:

- make the broker-native flow honest and safe in failure conditions

Include:

- denial path
- failure path
- retry classification
- bounded retry counters and retry exhaustion behavior
- order expiration handling
- audit details for denials and failures
- secret redaction checks

Checklist:

- [ ] Add denial-path handling.
- [ ] Add failure-path handling.
- [ ] Add retry classification and bounded retry behavior.
- [ ] Reject unsupported or malformed policy matcher entries fail-closed.
- [ ] Add secret-redaction checks.
- [ ] Add worker denial-path and failure-path tests.

Done when:

- denied requests land in `denied`
- failed requests land in `failed`
- expired orders land in `expired`
- failure behavior is tested and documented

## 7. Iteration 3: Broker-Native Challenge Expansion

Goal:

- add challenge behavior for broker-native workflows only

Include:

- explicit `no-challenge` path
- at least one broker-native challenge-provider path if needed
- clear separation between broker-native challenge logic and future ACME challenge behavior

Checklist:

- [ ] Implement the explicit `no-challenge` path.
- [ ] Implement at least one broker-native challenge-provider path if needed.
- [ ] Keep broker-native challenge logic separate from future ACME challenge behavior.

Done when:

- broker-native challenge flows work end to end
- the docs still clearly separate broker and ACME behavior

## 8. Iteration 4: Command-Based Issuer Integration

Goal:

- add a production-oriented issuer path safely

Include:

- hardened subprocess wrapper
- command-based issuer skeleton
- timeout, logging, and sanitized environment handling

Checklist:

- [ ] Use hardened subprocess wrappers.
- [ ] Implement a command-based issuer skeleton.
- [ ] Add subprocess timeout, logging, and sanitized environment handling tests.

Done when:

- command execution is controlled and tested
- the mock issuer path still works
- the implementation does not over-abstract issuer handling

## 9. Iteration 5: ACME Minimal Compatible Flow

Goal:

- implement the smallest ACME flow that is genuinely compatible with documented support

Include:

- directory
- nonce
- account creation
- External Account Binding for account creation
- order creation
- order polling
- authorization and challenge resources
- both `http-01` and `dns-01` challenge flows
- finalize
- certificate retrieval

Checklist:

- [ ] Implement the ACME resources defined in [`acme-api-reference.md`](./acme-api-reference.md).
- [ ] Keep ACME behavior protocol-correct and broker-internal behavior separate.
- [ ] Enforce identifier support rules, ownership checks, and DNS normalization.
- [ ] Require External Account Binding for ACME account creation.
- [ ] Implement both `http-01` and `dns-01` challenge flows.
- [ ] Advertise only the ACME features actually implemented.
- [ ] Run ACME integration tests against Pebble.
- [ ] Pass ACME protocol tests for the documented supported feature set.

Done when:

- the ACME adapter behaves correctly for the documented feature set
- protocol tests pass under `pytest`
- local ACME integration tests run against Pebble

## 10. Iteration 6: Compatibility Hardening

Goal:

- prove the ACME adapter works with real clients

Include:

- smoke-test flows with `certbot`
- smoke-test flows with `acme.sh`
- fixes needed for real interoperability gaps
- optional verification against Let’s Encrypt staging if useful and environment support exists

Checklist:

- [ ] Run a real-client smoke test with `certbot`.
- [ ] Run a real-client smoke test with `acme.sh`.
- [ ] Document any optional Let’s Encrypt staging verification separately from the default test flow.

Done when:

- both named-client smoke tests pass for the documented supported feature set
- compatibility docs match reality

## 11. Iteration 7: Optional ACME Expansion

Goal:

- add optional ACME features only after the core flow is stable

Possible additions:

- wildcard support if full `dns-01` support exists
- `revokeCert`
- `keyChange`
- `tls-alpn-01`

Rules:

- add one feature at a time
- update the ACME support matrix when a feature lands
- add tests before advertising the feature

## 12. Stop Rules

Pause and reassess if:

- the current iteration needs broad refactoring unrelated to its goal
- the code starts adding frameworks for features not yet implemented
- docs would need to claim support for behavior that is not yet working
- the implementation starts creating placeholder endpoints or placeholder plugin systems

## 13. Preferred Working Order

When in doubt, implement in this order:

1. broker-native happy path
2. denial and failure paths
3. broker-native challenge paths
4. command-based issuer support
5. ACME minimal compatible flow
6. real-client compatibility hardening
7. optional ACME feature expansion

## 14. MVP Done

The MVP is complete when:

- broker-native ordering works end to end
- worker processing is asynchronous and durable
- security defaults are active
- runtime state and artifacts are durable
- ACME behavior matches the documented supported feature set
- `certbot` and `acme.sh` smoke tests pass
- the default automated test path does not depend on live Let’s Encrypt services
- the code remains small enough to understand without a framework-heavy architecture
