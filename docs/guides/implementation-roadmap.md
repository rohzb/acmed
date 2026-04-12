# acmed Implementation Plan

For machine-friendly constraints and schemas, see [`../models/README.md`](../models/README.md).

## 1. Purpose

Build `acmed` in small, working slices.

This plan tells you:

- what to build first
- what each iteration must include
- what to delay
- the shortest actionable checklist for each iteration
- when to stop and reassess

Use the linked docs for topic-specific rules:

- [`system-architecture.md`](../architecture/system-architecture.md): runtime shape and boundaries
- [`data-model.md`](../architecture/data-model.md): lifecycle, persistence, and artifacts
- [`configuration.md`](../reference/configuration.md): config schema, issuer profiles, identity, and policy matching
- [`acme-api.md`](../reference/acme-api.md): primary ACME-visible protocol contract
- [`implementation-guide.md`](./implementation-guide.md): code-shape guidance and test expectations
- [`security-operations.md`](./security-operations.md): security and runtime posture
- [`broker-api.md`](../reference/broker-api.md): later secondary broker-native interface rules

## 2. Core Delivery Rule

Do not build for the final shape first.

Build the smallest correct slice, prove it works, then expand it.

## 3. Delivery Rules

Each iteration should:

1. Deliver working behavior, not structure-only stubs.
2. Add only the abstractions needed by the current iteration.
3. Keep tests green before moving to the next iteration.
4. Keep docs truthful about what is and is not supported.
5. Prefer simple wrappers around real issuer tools over speculative internal challenge systems.
6. Prefer simple code over speculative future-proof structure.
7. Keep security defaults on from the first iteration that exposes real behavior.

Testing baseline for every iteration:

- Python tests run under `pytest`
- local integration tests prefer deterministic local dependencies
- issuer integration uses Pebble by default rather than external network dependencies

## 4. Iteration 0: Bootstrapping

Goal:

- establish project layout, core models, config loading, and basic local execution

Include:

- package skeleton
- typed config models for token subjects, admin subjects, request limits, order TTL, claim TTL, retry bounds, proof handlers, and issuer profiles
- order models and state values
- order lifecycle state machine
- interfaces for authorizers, proof handlers, and issuers
- core error types
- basic app startup

Do not include yet:

- real issuer execution
- broker-native API endpoints
- broad plugin ecosystems

Checklist:

- [ ] Define typed config models.
- [ ] Define order models and state values.
- [ ] Implement the order lifecycle state machine.
- [ ] Define interfaces for authorizers, proof handlers, and issuers.
- [ ] Add core error types.
- [ ] Start the project locally with basic app startup.
- [ ] Run a basic `pytest` pass successfully.

Done when:

- the project starts locally
- config validation works
- basic tests run successfully

## 5. Iteration 1: ACME Happy Path

Goal:

- implement one complete ACME-driven issuance flow

Include:

- ACME directory and nonce
- ACME account creation with the documented enrollment rules
- ACME order creation, polling, finalize, and certificate retrieval for the supported slice
- SQLite order persistence
- worker pickup of `pending` orders
- one authorizer path
- one proof-handler path
- one issuer path using the mock issuer
- artifact write path

Do not include yet:

- high-privilege real issuer credentials
- broker-native API resources
- multiple proof modes unless one is needed for the slice

Checklist:

- [ ] Create SQLite schema for `orders`, `issuance_attempts`, and `audit_events`.
- [ ] Implement runtime-state storage helpers.
- [ ] Implement artifact layout and sensitive-file permissions.
- [ ] Implement audit-event writes.
- [ ] Implement deduplication key handling.
- [ ] Normalize ACME order requests.
- [ ] Enforce request size and SAN-count limits at the HTTP boundary.
- [ ] Parse and validate `allowed_domains` entries with explicit `syntax` and `value` fields.
- [ ] Support `exact` and `suffix` policy syntax in the initial policy matcher.
- [ ] Resolve policy and issuer/proof choices.
- [ ] Enforce CSR mode selection from `csr_pem` presence versus selected policy mode.
- [ ] Persist new orders as `pending`.
- [ ] Implement asynchronous worker pickup.
- [ ] Restrict worker claim pickup to `pending` and recoverable `authorized` orders.
- [ ] Transition orders through authorization, proof, issuance, and terminal states.
- [ ] Enforce ACME account authentication and resource ownership rules.
- [ ] Enforce TLS outside explicit local development mode.
- [ ] Enforce deny-by-default authorization.
- [ ] Redact secrets from logs and audit records.
- [ ] Implement at least one authorizer.
- [ ] Implement at least one proof handler.
- [ ] Implement the mock issuer.
- [ ] Configure `pytest` as the canonical Python test runner.
- [ ] Pass state-machine, config-validation, policy-matching, ACME-protocol, and happy-path worker tests.

Done when:

- an ACME order can reach certificate issuance successfully
- artifacts and audit records are written
- happy-path tests pass

## 6. Iteration 2: First Real Issuer Integration

Goal:

- add one real issuer path that uses external tooling and real challenge plugins

Include:

- one production-oriented issuer wrapper using either `acme.sh` or `certbot`
- hardened subprocess wrapper
- explicit issuer-profile configuration
- timeout, logging, and sanitized environment handling

Checklist:

- [ ] Implement one real issuer wrapper for `acme.sh` or `certbot`.
- [ ] Use hardened subprocess wrappers.
- [ ] Add issuer-profile config validation.
- [ ] Capture stdout, stderr, exit code, and artifact paths.
- [ ] Add subprocess timeout, logging, and sanitized environment handling tests.
- [ ] Add one deterministic local issuer integration test against Pebble or equivalent.

Done when:

- one non-mock issuer path works end to end
- command execution is controlled and tested
- the mock issuer path still works

## 7. Iteration 3: Failure And Denial Paths

Goal:

- make the ACME-first flow honest and safe in failure conditions

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
- [ ] Reject unsupported or malformed policy matcher entries fail closed.
- [ ] Add secret-redaction checks.
- [ ] Add worker denial-path and failure-path tests.

Done when:

- denied requests land in `denied`
- failed requests land in `failed`
- expired orders land in `expired`
- failure behavior is tested and documented

## 8. Iteration 4: Second Issuer And Capability Hardening

Goal:

- expand real issuer support without weakening policy boundaries

Include:

- the second real issuer wrapper when the first slice used only one of `acme.sh` or `certbot`
- issuer capability-scope validation and auditability
- policy tests that prove requesters cannot escalate into broader issuer power

Checklist:

- [ ] Add the second real issuer wrapper or document why only one remains in scope.
- [ ] Persist issuer-attempt metadata needed for audit and troubleshooting.
- [ ] Add tests for issuer restriction by policy.
- [ ] Add tests that requester-supplied `issuer_name` cannot bypass policy.

Done when:

- real issuer support is not mock-only
- issuer selection remains policy-restricted and tested

## 9. Iteration 5: Broker API Expansion

Goal:

- add the broker-native API only after the ACME-first service shape is stable

Include:

- create-order and read-order endpoints for internal integrations if still needed
- clear documentation that the broker API is additive and secondary
- integration validation only for the documented broker slice

Checklist:

- [ ] Decide whether the broker API is still needed.
- [ ] Implement only the documented secondary broker resources.
- [ ] Keep broker-native behavior additive and separate from the ACME contract.
- [ ] Run broker integration tests for the supported slice only.

Done when:

- the broker API remains secondary, truthful, and does not distort the ACME-first core

## 10. Stop Rules

Stop and reassess when:

- the implementation starts duplicating major behavior already available in `acme.sh` or `certbot`
- the broker core starts depending on one issuer adapter's internal flags or quirks
- policy can no longer be explained as the narrow boundary between requester permission and issuer capability
- the broker-native API would start distorting or duplicating the ACME-first product model
