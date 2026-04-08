# acmed Delivery Plan

> [!TIP]
> **TL;DR**
> Build `acmed` as a sequence of small, working, testable slices. Do not try to implement the full end-state architecture in the first pass.

For day-to-day implementation tracking, use [`implementation-checklist.md`](./implementation-checklist.md) alongside this document.

## 1. Purpose

Use this document to guide implementation sequencing.

The goal is to keep the project moving through working iterations instead of attempting a full, speculative implementation up front. Each iteration should leave the repository in a runnable, testable, and truthfully documented state.

Document boundaries:

- use [`architecture.md`](./architecture.md), [`data-model.md`](./data-model.md), [`policy-config.md`](./policy-config.md), [`broker-api-reference.md`](./broker-api-reference.md), and [`security-operations.md`](./security-operations.md) for the system contract
- use this document for sequencing, stop rules, and MVP completion
- use [`implementation-checklist.md`](./implementation-checklist.md) for day-to-day execution
- use [`acme-api-reference.md`](./acme-api-reference.md) for ACME-visible behavior

## 2. Core Delivery Rule

Do not build for the final shape first.

Build the smallest correct slice, prove it works, then expand it.

This should help both humans and coding models avoid:

- premature abstraction
- placeholder-heavy code
- unsupported feature claims
- large rewrites caused by trying to implement everything at once

## 3. Delivery Rules

Each iteration should follow these rules:

1. Deliver working behavior, not scaffolding-only structure.
2. Add only the abstractions needed by the current iteration.
3. Keep tests green before moving to the next iteration.
4. Keep documentation truthful about what is and is not supported.
5. Do not advertise unsupported ACME features or challenge types.
6. Refactor only when it improves the current slice or removes proven pain.
7. Prefer simple code now over “future-proof” code that is not yet needed.
8. Keep security defaults on from the first iteration that exposes real behavior.

## 4. Iteration Shape

Every iteration should contain:

- a concrete scope boundary
- a runnable or testable result
- explicit non-goals for that iteration
- tests that prove the slice works
- small doc updates that match the current behavior

Every iteration should end with:

- a working repository state
- passing tests for the features introduced in that iteration
- no knowingly false claims in docs or config examples

Testing baseline for every iteration:

- Python tests should run under `pytest`
- local integration tests should prefer deterministic local dependencies
- ACME integration should use Pebble by default rather than external network dependencies

## 5. Iteration 0: Bootstrapping

Goal:

- establish project layout, core models, config loading, and basic local execution

Include:

- package skeleton
- config parsing
- state model definitions
- error types
- basic app startup

Do not include yet:

- real issuer execution
- ACME endpoints
- broad plugin ecosystem

Done when:

- the project starts locally
- config validation works
- basic tests run successfully
- a basic `pytest` run succeeds

## 6. Iteration 1: Broker-Native Happy Path

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

Done when:

- a broker-native request can reach `issued`
- artifacts and audit records are written
- happy-path tests pass

## 7. Iteration 2: Failure And Denial Paths

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

Done when:

- denied requests land in `denied`
- failed requests land in `failed`
- expired orders land in `expired`
- failure behavior is tested and documented

## 8. Iteration 3: Broker-Native Challenge Expansion

Goal:

- add challenge behavior for broker-native workflows only

Include:

- explicit no-challenge path
- at least one broker-native challenge-provider path if needed
- clear separation between broker-native challenge logic and future ACME challenge behavior

Do not include yet:

- ACME challenge resources
- ACME client compatibility claims

Done when:

- broker-native challenge flows work end to end
- the docs still clearly separate broker and ACME behavior

## 9. Iteration 4: Command-Based Issuer Integration

Goal:

- add a production-oriented issuer path safely

Include:

- hardened subprocess wrapper
- command-based issuer skeleton
- timeout, logging, and sanitized environment handling

Done when:

- command execution is controlled and tested
- the mock issuer path still works
- the implementation does not over-abstract issuer handling

## 10. Iteration 5: ACME Minimal Compatible Flow

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

Use:

- [`acme-api-reference.md`](./acme-api-reference.md) as the protocol authority

Do not include yet unless truly supported:

- optional ACME endpoints
- unsupported challenge types
- compatibility claims for untested clients

Done when:

- the ACME adapter behaves correctly for the documented feature set
- protocol tests pass under `pytest`
- local ACME integration tests run against Pebble

## 11. Iteration 6: Compatibility Hardening

Goal:

- prove the ACME adapter works with real clients

Include:

- smoke-test flows with `certbot`
- smoke-test flows with `acme.sh`
- fixes needed for real interoperability gaps
- optional verification against Let’s Encrypt staging if useful and environment support exists

Done when:

- both named-client smoke tests pass for the documented supported feature set
- compatibility docs match reality

## 12. Iteration 7: Optional ACME Expansion

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

## 13. Stop Rules

Pause and reassess if:

- the current iteration needs broad refactoring unrelated to its goal
- the code starts adding frameworks for features not yet implemented
- docs would need to claim support for behavior that is not yet working
- the model starts creating placeholder endpoints or placeholder plugin systems

## 14. Refactoring Rules

Refactor when:

- the current slice is harder to understand because of duplication
- two real implementations prove a shared abstraction is now justified
- a security improvement needs a structural change

Do not refactor just to reach an imagined end-state architecture.

## 15. Preferred Working Order

When in doubt, implement in this order:

1. broker-native happy path
2. denial and failure paths
3. broker-native challenge paths
4. command-based issuer support
5. ACME minimal compatible flow
6. real-client compatibility hardening
7. optional ACME feature expansion

## 16. Done Criteria For The Overall MVP

The MVP is complete when:

- broker-native ordering works end to end
- security defaults are active
- runtime state and artifacts are durable
- ACME behavior matches the documented supported feature set
- `certbot` and `acme.sh` smoke tests pass
- the default automated test path does not depend on live Let’s Encrypt services
- the code remains small enough to understand without a framework-heavy architecture
